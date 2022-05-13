'''
Specify the core interventions. Other interventions can be
defined by the user by inheriting from these classes.
'''

import numpy as np
import sciris as sc
# import pandas as pd
# import scipy as sp
# import pylab as pl
import inspect
# import datetime as dt
# from . import misc as cvm
# from . import utils as cvu
# from . import base as cvb
from . import defaults as hpd
from . import parameters as hppar
from . import utils as hpu
# from . import immunity as cvi
# from collections import defaultdict


#%% Helper functions

def find_day(arr, t=None, interv=None, sim=None, which='first'):
    '''
    Helper function to find if the current simulation time matches any day in the
    intervention. Although usually never more than one index is returned, it is
    returned as a list for the sake of easy iteration.

    Args:
        arr (list/function): list of timepoints in the intervention, or a boolean array; or a function that returns these
        t (int): current simulation time (can be None if a boolean array is used)
        which (str): what to return: 'first', 'last', or 'all' indices
        interv (intervention): the intervention object (usually self); only used if arr is callable
        sim (sim): the simulation object; only used if arr is callable

    Returns:
        inds (list): list of matching timepoints; length zero or one unless which is 'all'

    New in version 2.1.2: arr can be a function with arguments interv and sim.
    '''
    if callable(arr):
        arr = arr(interv, sim)
        arr = sc.promotetoarray(arr)
    all_inds = sc.findinds(arr=arr, val=t)
    if len(all_inds) == 0 or which == 'all':
        inds = all_inds
    elif which == 'first':
        inds = [all_inds[0]]
    elif which == 'last':
        inds = [all_inds[-1]]
    else: # pragma: no cover
        errormsg = f'Argument "which" must be "first", "last", or "all", not "{which}"'
        raise ValueError(errormsg)
    return inds



#%% Generic intervention classes

__all__ = ['Intervention']


class Intervention:
    '''
    Base class for interventions.
    Args:
        label       (str): a label for the intervention (used for plotting, and for ease of identification)
        show_label (bool): whether or not to include the label in the legend
        do_plot    (bool): whether or not to plot the intervention
        line_args  (dict): arguments passed to pl.axvline() when plotting
    '''
    def __init__(self, label=None, show_label=False, do_plot=None, line_args=None):
        self._store_args() # Store the input arguments so the intervention can be recreated
        if label is None: label = self.__class__.__name__ # Use the class name if no label is supplied
        self.label = label # e.g. "Screen"
        self.show_label = show_label # Do not show the label by default
        self.do_plot = do_plot if do_plot is not None else True # Plot the intervention, including if None
        self.line_args = sc.mergedicts(dict(linestyle='--', c='#aaa', lw=1.0), line_args) # Do not set alpha by default due to the issue of overlapping interventions
        self.timepoints = [] # The start and end timepoints of the intervention
        self.initialized = False # Whether or not it has been initialized
        self.finalized = False # Whether or not it has been initialized
        return


    def __repr__(self, jsonify=False):
        ''' Return a JSON-friendly output if possible, else revert to short repr '''

        if self.__class__.__name__ in __all__ or jsonify:
            try:
                json = self.to_json()
                which = json['which']
                pars = json['pars']
                parstr = ', '.join([f'{k}={v}' for k,v in pars.items()])
                output = f"cv.{which}({parstr})"
            except Exception as E:
                output = f'{type(self)} (error: {str(E)})' # If that fails, print why
            return output
        else:
            return f'{self.__module__}.{self.__class__.__name__}()'


    def __call__(self, *args, **kwargs):
        # Makes Intervention(sim) equivalent to Intervention.apply(sim)
        if not self.initialized:  # pragma: no cover
            errormsg = f'Intervention (label={self.label}, {type(self)}) has not been initialized'
            raise RuntimeError(errormsg)
        return self.apply(*args, **kwargs)


    def disp(self):
        ''' Print a detailed representation of the intervention '''
        return sc.pr(self)


    def _store_args(self):
        ''' Store the user-supplied arguments for later use in to_json '''
        f0 = inspect.currentframe() # This "frame", i.e. Intervention.__init__()
        f1 = inspect.getouterframes(f0) # The list of outer frames
        parent = f1[2].frame # The parent frame, e.g. change_beta.__init__()
        _,_,_,values = inspect.getargvalues(parent) # Get the values of the arguments
        if values:
            self.input_args = {}
            for key,value in values.items():
                if key == 'kwargs': # Store additional kwargs directly
                    for k2,v2 in value.items(): # pragma: no cover
                        self.input_args[k2] = v2 # These are already a dict
                elif key not in ['self', '__class__']: # Everything else, but skip these
                    self.input_args[key] = value
        return


    def initialize(self, sim=None):
        '''
        Initialize intervention -- this is used to make modifications to the intervention
        that can't be done until after the sim is created.
        '''
        self.initialized = True
        self.finalized = False
        return


    def finalize(self, sim=None):
        '''
        Finalize intervention

        This method is run once as part of `sim.finalize()` enabling the intervention to perform any
        final operations after the simulation is complete (e.g. rescaling)
        '''
        if self.finalized: # pragma: no cover
            raise RuntimeError('Intervention already finalized')  # Raise an error because finalizing multiple times has a high probability of producing incorrect results e.g. applying rescale factors twice
        self.finalized = True
        return


    def apply(self, sim):
        '''
        Apply the intervention. This is the core method which each derived intervention
        class must implement. This method gets called at each timestep and can make
        arbitrary changes to the Sim object, as well as storing or modifying the
        state of the intervention.

        Args:
            sim: the Sim instance

        Returns:
            None
        '''
        raise NotImplementedError


    def shrink(self, in_place=False):
        '''
        Remove any excess stored data from the intervention; for use with sim.shrink().

        Args:
            in_place (bool): whether to shrink the intervention (else shrink a copy)
        '''
        if in_place: # pragma: no cover
            return self
        else:
            return sc.dcp(self)


    def plot_intervention(self, sim, ax=None, **kwargs):
        '''
        Plot the intervention

        This can be used to do things like add vertical lines at timepoints when
        interventions take place. Can be disabled by setting self.do_plot=False.

        Note 1: you can modify the plotting style via the ``line_args`` argument when
        creating the intervention.

        Note 2: By default, the intervention is plotted at the timepoints stored in self.timepoints.
        However, if there is a self.plot_timepoints attribute, this will be used instead.

        Args:
            sim: the Sim instance
            ax: the axis instance
            kwargs: passed to ax.axvline()

        Returns:
            None
        '''
        line_args = sc.mergedicts(self.line_args, kwargs)
        if self.do_plot or self.do_plot is None:
            if ax is None:
                ax = pl.gca()
            if hasattr(self, 'plot_timepoints'):
                timepoints = self.plot_timepoints
            else:
                timepoints = self.timepoints
            if sc.isiterable(timepoints):
                label_shown = False # Don't show the label more than once
                for timepoint in timepoints:
                    if sc.isnumber(timepoint):
                        if self.show_label and not label_shown: # Choose whether to include the label in the legend
                            label = self.label
                            label_shown = True
                        else:
                            label = None
                        # date = sc.date(sim.date(day))
                        # ax.axvline(date, label=label, **line_args)
        return


    def to_json(self):
        '''
        Return JSON-compatible representation

        Custom classes can't be directly represented in JSON. This method is a
        one-way export to produce a JSON-compatible representation of the
        intervention. In the first instance, the object dict will be returned.
        However, if an intervention itself contains non-standard variables as
        attributes, then its `to_json` method will need to handle those.

        Note that simply printing an intervention will usually return a representation
        that can be used to recreate it.

        Returns:
            JSON-serializable representation (typically a dict, but could be anything else)
        '''
        which = self.__class__.__name__
        pars = sc.jsonify(self.input_args)
        output = dict(which=which, pars=pars)
        return output


class dynamic_pars(Intervention):
    '''
    A generic intervention that modifies a set of parameters at specified points
    in time.

    The intervention takes a single argument, pars, which is a dictionary of which
    parameters to change, with following structure: keys are the parameters to change,
    then subkeys 'days' and 'vals' are either a scalar or list of when the change(s)
    should take effect and what the new value should be, respectively.

    You can also pass parameters to change directly as keyword arguments.

    Args:
        pars (dict): described above
        kwargs (dict): passed to Intervention()

    **Examples**::
        interv = hp.dynamic_pars(condoms=dict(timepoints=10, vals={'c':0.9})) # Increase condom use amount casual partners to 90%
        interv = hp.dynamic_pars({'beta':{'timepoints':[10, 15], 'vals':[0.005, 0.015]}, # At timepoint 10, reduce beta, then increase it again
                                  'debut':{'timepoints':10, 'vals':dict(f=dict(dist='normal', par1=20, par2=2.1), m=dict(dist='normal', par1=19.6, par2=1.8))}}) # Increase mean age of sexual debut
    '''

    def __init__(self, pars=None, **kwargs):

        # Find valid sim parameters and move matching keyword arguments to the pars dict
        pars = sc.mergedicts(pars) # Ensure it's a dictionary
        sim_par_keys = list(hppar.make_pars().keys()) # Get valid sim parameters
        kwarg_keys = [k for k in kwargs.keys() if k in sim_par_keys]
        for kkey in kwarg_keys:
            pars[kkey] = kwargs.pop(kkey)

        # Do standard initialization
        super().__init__(**kwargs) # Initialize the Intervention object

        # Handle the rest of the initialization
        subkeys = ['timepoints', 'vals']
        for parkey in pars.keys():
            for subkey in subkeys:
                if subkey not in pars[parkey].keys(): # pragma: no cover
                    errormsg = f'Parameter {parkey} is missing subkey {subkey}'
                    raise sc.KeyNotFoundError(errormsg)
                if sc.isnumber(pars[parkey][subkey]):
                    pars[parkey][subkey] = sc.promotetoarray(pars[parkey][subkey])
                else:
                    pars[parkey][subkey] = sc.promotetolist(pars[parkey][subkey])
            # timepoints = pars[parkey]['timepoints']
            # vals = pars[parkey]['vals']
            # if sc.isiterable(timepoints):
            #     len_timepoints = len(timepoints)
            #     len_vals = len(vals)
            #     if len_timepoints != len_vals:
            #         raise ValueError(f'Length of timepoints ({len_timepoints}) does not match length of values ({len_vals}) for parameter {parkey}')
        self.pars = pars

        return

    def initialize(self, sim):
        ''' Initialize with a sim '''
        for parkey in self.pars.keys():
            try: # First try to interpret the timepoints as dates
                tps = sim.get_t(self.pars[parkey]['timepoints'])  # Translate input to timepoints
            except:
                tps = []
                # See if it's in the time vector
                for tp in self.pars[parkey]['timepoints']:
                    if tp in sim.tvec:
                        tps.append(tp)
                    else: # Give up
                        errormsg = f'Could not parse timepoints provided for {parkey}.'
                        raise ValueError(errormsg)
            self.pars[parkey]['processed_timepoints'] = sc.promotetoarray(tps)
        self.initialized = True
        return


    def apply(self, sim):
        ''' Loop over the parameters, and then loop over the timepoints, applying them if any are found '''
        t = sim.t
        for parkey,parval in self.pars.items():
            if t in parval['processed_timepoints']: # TODO: make this more robust
                self.timepoints.append(t)
                ind = sc.findinds(parval['processed_timepoints'], t)[0]
                val = parval['vals'][ind]
                if isinstance(val, dict):
                    sim[parkey].update(val) # Set the parameter if a nested dict
                else:
                    sim[parkey] = val # Set the parameter if not a dict
        return



class init_states(Intervention):
    '''
    An intervention to initialize people into disease states and confer historical immunity

    Args:
        init_hpv_prev (float/arr/dict): accepts a float, an array describing prevalence by age, or a dictionary keyed by sex with values that are floats or arrays by age.

    **Examples**::
        interv = cv.init_states(init_hpv_prev=0.08, init_cin_prev=0.01, init_cancer_prev=0.001)
    '''

    def __init__(self, age_brackets=None, init_hpv_prev=None): # init_cin_prev=None, init_cancer_prev=None):

        # Assign age brackets
        if age_brackets is not None:
            self.age_brackets = age_brackets
        else:
            self.age_brackets = np.array([150]) # Use an arbitrarily high upper age bracket
        self.n_age_brackets = len(self.age_brackets)

        # Assign the rest of the variables, including error checking on types and length
        self.init_hpv_prev = self.validate(init_hpv_prev, by_sex=True)
        # self.init_cin_prev = self.validate(init_cin_prev)
        self.init_cancer_prev = self.validate(init_cancer_prev)

        return


    def validate(self, var, by_sex=False):
        '''
        Initial prevalence values can be supplied with different amounts of detail.
        Here we flesh out any missing details so that the initial prev values are
        by age and genotype.
        '''

        # Helper function to check that prevalence values are ok
        def validate_arrays(vals):
            if len(vals) not in [1, self.n_age_brackets]:
                errormsg = f'The initial prevalence values must either be floats or arrays of length {self.n_age_brackets}, not length {len(vals)}.'
                raise ValueError(errormsg)
            if vals.any() < 0 or vals.any() > 1:
                errormsg = f'The initial prevalence values must either between 0 and 1, not {vals}.'
                raise ValueError(errormsg)

        # If this variable is by sex, check types and construct a dictionary of arrays
        if by_sex:
            sex_keys = {'m', 'f'}

            # If values have been provided, validate them
            if var is not None:
                if sc.checktype(var, dict):
                    # If it's a dict, it needs to be keyed by sex
                    if set(var.keys()) != sex_keys:
                        errormsg = f'If supplying a dictionary of initial prevalence values to init_states, the keys must be "m" and "f", not {var.keys()}.'
                        raise ValueError(errormsg)
                    for sk, vals in var.items():
                        var[sk] = sc.promotetoarray(vals)
                elif sc.checktype(var, 'arraylike') or sc.isnumber(var):
                    # If it's an array, assume these values apply to males and females
                    var = {sk: sc.promotetoarray(var) for sk in sex_keys}
                else:
                    errormsg = f'Initial prevalence values of type {type(var)} not recognized, must be a dict with keys "m" and "f", an array, or a float.'
                    raise ValueError(errormsg)

                # Now validate the arrays
                for sk, vals in var.items():
                    validate_arrays(vals)

            # If values haven't been supplied, assume zero
            else:
                var = {'f': np.array([0]), 'm': np.array([0])}

        # If this variable is not by sex, check types and construct an array
        else:
            if sc.checktype(var, 'arraylike') or sc.isnumber(var):
                var = validate_arrays(sc.promotetoarray(var))
            else:
                errormsg = f'Initial prevalence values of type {type(var)} not recognized, must be an array or a float.'
                raise ValueError(errormsg)

        return var


    def apply(self, sim):
        ''' Applying the intervention happens on the first simulation step '''
        if sim.t != 0:
            return

        # Shorten key variables
        ng = sim['n_genotypes']
        people = sim.people

        # Error checking and validation
        if sim['init_hpv_prev'] is not None:
            errormsg = f'Cannot use the init_states intervention if init_hpv_prev is not None; here it is {sim["init_hpv_prev"]}.'
            raise ValueError(errormsg)

        # Assign people to age buckets
        age_inds = np.digitize(people.age, self.age_brackets)

        # Assign probabilities of having HPV to each age/sex group
        hpv_probs = np.full(len(people), np.nan, dtype=hpd.default_float)
        hpv_probs[people.f_inds] = self.init_hpv_prev['f'][age_inds[people.f_inds]]
        hpv_probs[people.m_inds] = self.init_hpv_prev['m'][age_inds[people.m_inds]]

        # Get indices of people who have HPV (for now, split evenly between genotypes)
        hpv_inds = hpu.true(hpu.binomial_arr(hpv_probs))
        genotypes = np.random.randint(0, ng, len(hpv_inds))

        # Figure of duration of infection and infect people
        dur_inf = hpu.sample(**sim['dur']['inf'], size=len(hpv_inds))
        t_imm_event = np.floor(np.random.uniform(-dur_inf,0) / sim['dt'])
        _ = people.infect(inds=hpv_inds, genotypes=genotypes, offset=t_imm_event, dur_inf=dur_inf, layer='seed_infection')

        # Check for anyone who's already got CIN and cancer
        for g in range(ng):
            _ = people.check_cin1(g)
            _ = people.check_cin2(g)
            _ = people.check_cin3(g)
            _ = people.check_cancer(g)

        return

