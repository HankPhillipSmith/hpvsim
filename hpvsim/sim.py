'''
Define core Sim classes
'''

# Imports
import numpy as np
import pandas as pd
import sciris as sc
from . import base as hpb
from . import misc as hpm
from . import defaults as hpd
from . import utils as hpu
from . import population as hppop
from . import parameters as hppar
from .settings import options as hpo


# Define the model
class Sim(hpb.BaseSim):

    def __init__(self, pars=None, label=None,
                 popfile=None, people=None, version=None, **kwargs):

        # Set attributes
        self.label         = label    # The label/name of the simulation
        self.created       = None     # The datetime the sim was created
        self.popfile       = popfile  # The population file
        self.popdict       = people   # The population dictionary
        self.people        = None     # Initialize these here so methods that check their length can see they're empty
        self.t             = None     # The current time in the simulation (during execution); outside of sim.step(), its value corresponds to next timestep to be computed
        self.results       = {}       # For storing results
        self.summary       = None     # For storing a summary of the results
        self.initialized   = False    # Whether or not initialization is complete
        self.complete      = False    # Whether a simulation has completed running
        self.results_ready = False    # Whether or not results are ready
        self._default_ver  = version  # Default version of parameters used
        self._orig_pars    = None     # Store original parameters to optionally restore at the end of the simulation

        # Make default parameters (using values from parameters.py)
        default_pars = hppar.make_pars(version=version) # Start with default pars
        super().__init__(default_pars) # Initialize and set the parameters as attributes

        # Update pars
        self.update_pars(pars, **kwargs)   # Update the parameters, if provided

        return


    def initialize(self, reset=False, init_infections=True, **kwargs):
        '''
        Perform all initializations on the sim.
        '''
        self.t = 0  # The current time index
        self.validate_pars() # Ensure parameters have valid values
        self.set_seed() # Reset the random seed before the population is created
        self.init_results() # After initializing the variant, create the results structure
        self.init_people(reset=reset, init_infections=init_infections, **kwargs) # Create all the people (the heaviest step)
        self.set_seed() # Reset the random seed again so the random number stream is consistent
        self.initialized   = True
        self.complete      = False
        self.results_ready = False
        return self


    def validate_pars(self, validate_layers=True):
        '''
        Some parameters can take multiple types; this makes them consistent.

        Args:
            validate_layers (bool): whether to validate layer parameters as well via validate_layer_pars() -- usually yes, except during initialization
        '''

        # Handle types
        for key in ['pop_size', 'pop_infected']:
            try:
                self[key] = int(self[key])
            except Exception as E:
                errormsg = f'Could not convert {key}={self[key]} of {type(self[key])} to integer'
                raise ValueError(errormsg) from E

        # Handle start
        if self['start'] in [None, 0]: # Use default start
            self['start'] = 2015

        # Handle end and n_years
        if self['end']:
            self['n_years'] = self['end'] - self['start']
            if self['n_years'] <= 0:
                errormsg = f"Number of years must be >0, but you supplied start={str(self['start'])} and end={str(self['end'])}, which gives n_years={self['n_years']}"
                raise ValueError(errormsg)
        else:
            if self['n_years']:
                self['end'] = self['start'] + self['n_years']
            else:
                errormsg = f'You must supply one of n_years and end_day."'
                raise ValueError(errormsg)
        
        # Construct other things that keep track of time
        self.years          = sc.inclusiverange(self['start'],self['end'])
        self.yearvec        = sc.inclusiverange(start=self['start'], stop=self['end'], step=self['dt'])
        self.npts           = len(self.yearvec)
        self.tvec          = np.arange(self.npts)
        
        # Handle population network data
        network_choices = ['random', 'basic']
        choice = self['network']
        if choice and choice not in network_choices: # pragma: no cover
            choicestr = ', '.join(network_choices)
            errormsg = f'Population type "{choice}" not available; choices are: {choicestr}'
            raise ValueError(errormsg)

        # Handle verbose
        if self['verbose'] == 'brief':
            self['verbose'] = -1
        if not sc.isnumber(self['verbose']): # pragma: no cover
            errormsg = f'Verbose argument should be either "brief", -1, or a float, not {type(self["verbose"])} "{self["verbose"]}"'
            raise ValueError(errormsg)

        return


    def init_results(self):
        '''
        Create the main results structure.
        We differentiate between flows, stocks, and cumulative results
        The prefix "new" is used for flow variables, i.e. counting new events (infections/deaths/recoveries) on each timestep
        The prefix "n" is used for stock variables, i.e. counting the total number in any given state (sus/inf/rec/etc) on any particular timestep
        The prefix "cum" is used for cumulative variables, i.e. counting the total number that have ever been in a given state at some point in the sim
        Note that, by definition, n_dead is the same as cum_deaths and n_recovered is the same as cum_recoveries, so we only define the cumulative versions
        '''

        def init_res(*args, **kwargs):
            ''' Initialize a single result object '''
            output = hpb.Result(*args, **kwargs, npts=self.npts)
            return output

        dcols = hpd.get_default_colors() # Get default colors

        # Flows and cumulative flows
        for key,label in hpd.result_flows.items():
            self.results[f'cum_{key}'] = init_res(f'Cumulative {label}', color=dcols[key])  # Cumulative variables -- e.g. "Cumulative infections"

        for key,label in hpd.result_flows.items(): # Repeat to keep all the cumulative keys together
            self.results[f'new_{key}'] = init_res(f'Number of new {label}', color=dcols[key]) # Flow variables -- e.g. "Number of new infections"

        # Stock variables
        for key,label in hpd.result_stocks.items():
            self.results[f'n_{key}'] = init_res(label, color=dcols[key])

        # Other variables
        self.results['n_imports']           = init_res('Number of imported infections', scale=True)
        self.results['n_alive']             = init_res('Number alive', scale=True)
        self.results['n_naive']             = init_res('Number never infected', scale=True)
        self.results['n_removed']           = init_res('Number removed', scale=True, color=dcols.recovered)
        self.results['prevalence']          = init_res('Prevalence', scale=False)
        self.results['incidence']           = init_res('Incidence', scale=False)
        self.results['frac_vaccinated']     = init_res('Proportion vaccinated', scale=False)

        # Populate the rest of the results
        self.results['year'] = self.yearvec
        self.results['t']    = self.tvec
        self.results_ready   = False

        return


    def init_people(self, popdict=None, init_infections=False, reset=False, verbose=None, **kwargs):
        '''
        Create the people and the network.

        Use ``init_infections=False`` for creating a fresh People object for use
        in future simulations

        Args:
            popdict         (any):  pre-generated people of various formats.
            init_infections (bool): whether to initialize infections (default false when called directly)
            reset           (bool): whether to regenerate the people even if they already exist
            verbose         (int):  detail to print
            kwargs          (dict): passed to hp.make_people()
        '''

        # Handle inputs
        if verbose is None:
            verbose = self['verbose']
        if popdict is not None:
            self.popdict = popdict
        if verbose > 0:
            resetstr= ''
            if self.people:
                resetstr = ' (resetting people)' if reset else ' (warning: not resetting sim.people)'
            print(f'Initializing sim{resetstr} with {self["pop_size"]:0n} people')
        if self.popfile and self.popdict is None: # If there's a popdict, we initialize it
            self.load_population(init_people=False)

        # Actually make the people
        microstructure = self['network']
        self.people = hppop.make_people(self, reset=reset, verbose=verbose, microstructure=microstructure, **kwargs)
        self.people.initialize(sim_pars=self.pars) # Fully initialize the people
        self.reset_layer_pars(force=False) # Ensure that layer keys match the loaded population
        if init_infections:
            self.init_infections(verbose=verbose)

        return self


    def reset_layer_pars(self, layer_keys=None, force=False):
        '''
        Reset the parameters to match the population.

        Args:
            layer_keys (list): override the default layer keys (use stored keys by default)
            force (bool): reset the parameters even if they already exist
        '''
        if layer_keys is None:
            if self.people is not None: # If people exist
                layer_keys = self.people.contacts.keys()
            elif self.popdict is not None:
                layer_keys = self.popdict['layer_keys']
        hppar.reset_layer_pars(self.pars, layer_keys=layer_keys, force=force)
        return


    def init_infections(self, verbose=None):
        '''
        Initialize prior immunity and seed infections.
        Copied from Covasim. TODO: think of a better initialization strategy
        '''

        if verbose is None:
            verbose = self['verbose']

        # If anyone is non-naive, don't re-initialize
        if self.people.count_not('naive') == 0: # Everyone is naive

            # Create the seed infections
            if self['pop_infected']:
                inds = hpu.choose(self['pop_size'], self['pop_infected'])
                self.people.infect(inds=inds, layer='seed_infection') # Not counted by results since flows are re-initialized during the step

        elif verbose:
            print(f'People already initialized with {self.people.count_not("naive")} people non-naive and {self.people.count("infectious")} infectious; not reinitializing')

        return


    def step(self):
        ''' Step through time and update values '''

        # Set the time and if we have reached the end of the simulation, then do nothing
        if self.complete:
            raise AlreadyRunError('Simulation already complete (call sim.initialize() to re-run)')

        # Shorten key variables
        dt = self['dt'] # Timestep; TODO centralize this somewhere
        t = self.t
        ng = self['n_genotypes']
        acts = self['acts']
        condoms = self['condoms']
        eff_condoms = self['eff_condoms']
        rel_beta = self['rel_beta']
        people = self.people
        prel_trans = people.rel_trans

        # Update states and partnerships
        people.update_states_pre(t=t) # NB this also ages people and applies deaths
        n_dissolved = people.dissolve_partnerships(t=t) # Dissolve partnerships
        people.create_partnerships(t=t, n_new=n_dissolved) # Create new partnerships (maintaining the same overall partnerhip rate)
        contacts = people.contacts

        # Loop over genotypes and infect people
        sus = people.susceptible
        inf = people.infectious

        # Iterate through genotypes to calculate infections
        for genotype in range(ng):

            # Deal with genotype parameters
            # if genotype:
            #     genotype_label = self.pars['genotype_map'][genotype]
            #     rel_beta *= self['genotype_pars'][genotype_label]['rel_beta']
            beta = hpd.default_float(self['beta'] * rel_beta)
            foi_frac, foi_whole = 1, 1

            for lkey, layer in contacts.items():
                f = layer['f']
                m = layer['m']
                frac_acts, whole_acts = np.modf(acts[lkey]*dt) # Get the number of acts per timestep for this layer
                whole_acts = int(whole_acts)

                # Compute relative transmission and susceptibility
                # inf_genotype = people.infectious * (people.infectious_genotype == genotype) 
                # sus_imm = people.sus_imm[genotype,:]
                # rel_trans, rel_sus = hpu.compute_trans_sus(inf_genotype, sus, beta_layer, viral_load, symp, diag, sus_imm)

                # Compute transmissibility and infections
                foi = hpu.compute_foi( prel_trans, beta, condoms[lkey], eff_condoms, whole_acts, frac_acts, inf)#(foi_frac, foi_whole, inf)
                source_inds, target_inds = hpu.compute_infections(foi, f, m)  # Calculate transmission
                people.infect(inds=target_inds, source=source_inds, layer=lkey, genotype=genotype)  # Actually infect people

        # Update counts for this time step: stocks
        for key in hpd.result_stocks.keys():
            self.results[f'n_{key}'][t] = people.count(key)
        # for key in hpd.result_stocks_by_genotype.keys():
        #     for variant in range(ng):
        #         self.results['genotype'][f'n_{key}'][genotype, t] = people.count_by_genotype(key, genotype)

        # Update counts for this time step: flows
        for key,count in people.flows.items():
            self.results[key][t] += count
        # for key,count in people.flows_genotype.items():
        #     for variant in range(ng):
        #         self.results['genotype'][key][genotype][t] += count[genotype]

        # Tidy up
        self.t += 1
        if self.t == self.npts:
            self.complete = True

        return


    def run(self, do_plot=False, until=None, restore_pars=True, reset_seed=True, verbose=None):
        ''' Run the model once '''
        # Initialization steps -- start the timer, initialize the sim and the seed, and check that the sim hasn't been run
        T = sc.timer()

        if not self.initialized:
            self.initialize()
            self._orig_pars = sc.dcp(self.pars) # Create a copy of the parameters, to restore after the run, in case they are dynamically modified

        if verbose is None:
            verbose = self['verbose']

        if reset_seed:
            # Reset the RNG. If the simulation is newly created, then the RNG will be reset by sim.initialize() so the use case
            # for resetting the seed here is if the simulation has been partially run, and changing the seed is required
            self.set_seed()

        # Check for AlreadyRun errors
        errormsg = None
        until = self.npts if until is None else self.day(until)
        if until > self.npts:
            errormsg = f'Requested to run until t={until} but the simulation end is t={self.npts}'
        if self.t >= until: # NB. At the start, self.t is None so this check must occur after initialization
            errormsg = f'Simulation is currently at t={self.t}, requested to run until t={until} which has already been reached'
        if self.complete:
            errormsg = 'Simulation is already complete (call sim.initialize() to re-run)'
        if self.people.t not in [self.t, self.t-1]: # Depending on how the sim stopped, either of these states are possible
            errormsg = f'The simulation has been run independently from the people (t={self.t}, people.t={self.people.t}): if this is intentional, manually set sim.people.t = sim.t. Remember to save the people object before running the sim.'
        if errormsg:
            raise AlreadyRunError(errormsg)

        # Main simulation loop
        while self.t < until:

            # Check if we were asked to stop
            elapsed = T.toc(output=True)
            if self['timelimit'] and elapsed > self['timelimit']:
                sc.printv(f"Time limit ({self['timelimit']} s) exceeded; call sim.finalize() to compute results if desired", 1, verbose)
                return
            elif self['stopping_func'] and self['stopping_func'](self):
                sc.printv("Stopping function terminated the simulation; call sim.finalize() to compute results if desired", 1, verbose)
                return

            # Print progress
            if verbose:
                simlabel = f'"{self.label}": ' if self.label else ''
                string = f'  Running {simlabel}{self.yearvec[self.t]} ({self.t:2.0f}/{self.npts}) ({elapsed:0.2f} s) '
                if verbose >= 2:
                    sc.heading(string)
                elif verbose>0:
                    if not (self.t % int(1.0/verbose)):
                        sc.progressbar(self.t+1, self.npts, label=string, length=20, newline=True)

            # Do the heavy lifting -- actually run the model!
            self.step()

        # If simulation reached the end, finalize the results
        if self.complete:
            self.finalize(verbose=verbose, restore_pars=restore_pars)
            sc.printv(f'Run finished after {elapsed:0.2f} s.\n', 1, verbose)
        return self


    def finalize(self, verbose=None, restore_pars=True):
        ''' Compute final results '''

        if self.results_ready:
            # Because the results are rescaled in-place, finalizing the sim cannot be run more than once or
            # otherwise the scale factor will be applied multiple times
            raise AlreadyRunError('Simulation has already been finalized')

        # Calculate cumulative results
        for key in hpd.result_flows.keys():
            self.results[f'cum_{key}'][:] = np.cumsum(self.results[f'new_{key}'][:], axis=0)
        for res in [self.results['cum_infections']]: # Include initially infected people
            res.values += self['pop_infected']

        # Final settings
        self.results_ready = True # Set this first so self.summary() knows to print the results
        self.t -= 1 # During the run, this keeps track of the next step; restore this be the final day of the sim

        # Perform calculations on results
        self.compute_results(verbose=verbose) # Calculate the rest of the results
        self.results = sc.objdict(self.results) # Convert results to a odicts/objdict to allow e.g. sim.results.diagnoses

        # Optionally print summary output
        if verbose: # Verbose is any non-zero value
            if verbose>0: # Verbose is any positive number
                self.summarize() # Print medium-length summary of the sim
            else:
                self.brief() # Print brief summary of the sim

        return


    def compute_results(self, verbose=None):
        ''' Perform final calculations on the results '''
        self.compute_states()
        return


    def compute_states(self):
        '''
        Compute prevalence, incidence, and other states.
        '''
        res = self.results
        self.results['n_alive'][:]         = self['pop_size'] # Number of people still alive. TODO: add vital dynamics
        # self.results['n_naive'][:]         = self.scaled_pop_size - res['cum_deaths'][:] - res['n_recovered'][:] - res['n_exposed'][:] # Number of people naive
        self.results['n_susceptible'][:]   = res['n_alive'][:] - res['n_infectious'][:] - res['cum_recoveries'][:] # Recalculate the number of susceptible people, not agents
        # self.results['n_preinfectious'][:] = res['n_exposed'][:] - res['n_infectious'][:] # Calculate the number not yet infectious: exposed minus infectious
        # self.results['n_removed'][:]       = count_recov*res['cum_recoveries'][:] + res['cum_deaths'][:] # Calculate the number removed: recovered + dead
        self.results['prevalence'][:]      = res['n_infectious'][:]/res['n_alive'][:] # Calculate the prevalence
        self.results['incidence'][:]       = res['new_infections'][:]/res['n_susceptible'][:] # Calculate the incidence
        # self.results['frac_vaccinated'][:] = res['n_vaccinated'][:]/res['n_alive'][:] # Calculate the fraction vaccinated

        return


    def compute_summary(self, t=None, update=True, output=False, require_run=False):
        '''
        Compute the summary dict and string for the sim. Used internally; see
        sim.summarize() for the user version.

        Args:
            t (int/str): day or date to compute summary for (by default, the last point)
            update (bool): whether to update the stored sim.summary
            output (bool): whether to return the summary
            require_run (bool): whether to raise an exception if simulations have not been run yet
        '''
        if t is None:
            t = -1

        # Compute the summary
        if require_run and not self.results_ready:
            errormsg = 'Simulation not yet run'
            raise RuntimeError(errormsg)

        summary = sc.objdict()
        for key in self.result_keys():
            summary[key] = self.results[key][t]

        # Update the stored state
        if update:
            self.summary = summary

        # Optionally return
        if output:
            return summary
        else:
            return


    def summarize(self, full=False, t=None, sep=None, output=False):
        '''
        Print a medium-length summary of the simulation, drawing from the last time
        point in the simulation by default. Called by default at the end of a sim run.
        See also sim.disp() (detailed output) and sim.brief() (short output).

        Args:
            full   (bool):    whether or not to print all results (by default, only cumulative)
            t      (int/str): day or date to compute summary for (by default, the last point)
            sep    (str):     thousands separator (default ',')
            output (bool):    whether to return the summary instead of printing it

        **Examples**::

            sim = cv.Sim(label='Example sim', verbose=0) # Set to run silently
            sim.run() # Run the sim
            sim.summarize() # Print medium-length summary of the sim
            sim.summarize(t=24, full=True) # Print a "slice" of all sim results on day 24
        '''
        # Compute the summary
        summary = self.compute_summary(t=t, update=False, output=True)

        # Construct the output string
        if sep is None: sep = hpo.sep # Default separator
        labelstr = f' "{self.label}"' if self.label else ''
        string = f'Simulation{labelstr} summary:\n'
        for key in self.result_keys():
            if full or key.startswith('cum_'):
                val = np.round(summary[key])
                string += f'   {val:10,.0f} {self.results[key].name.lower()}\n'.replace(',', sep) # Use replace since it's more flexible

        # Print or return string
        if not output:
            print(string)
        else:
            return string


    def plot(self, toplot=None):
        ''' Plot the outputs of the model '''
        pass



class AlreadyRunError(RuntimeError):
    '''
    This error is raised if a simulation is run in such a way that no timesteps
    will be taken. This error is a distinct type so that it can be safely caught
    and ignored if required, but it is anticipated that most of the time, calling
    sim.run() and not taking any timesteps, would be an inadvertent error.
    '''
    pass
