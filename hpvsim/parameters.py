'''
Set the parameters for hpvsim.
'''

import numpy as np
import sciris as sc
import pandas as pd
from .settings import options as hpo # For setting global options
from . import misc as hpm
from . import utils as hpu
from . import defaults as hpd
from .data import loaders as hpdata

__all__ = ['make_pars', 'reset_layer_pars']


def make_pars(**kwargs):
    '''
    Create the parameters for the simulation. Typically, this function is used
    internally rather than called by the user; e.g. typical use would be to do
    sim = hpv.Sim() and then inspect sim.pars, rather than calling this function
    directly.

    Args:
        version       (str):  if supplied, use parameters from this version
        kwargs        (dict): any additional kwargs are interpreted as parameter names

    Returns:
        pars (dict): the parameters of the simulation
    '''
    pars = {}

    # Population parameters
    pars['n_agents']        = 20e3      # Number of agents
    pars['total_pop']       = None      # If defined, used for calculating the scale factor
    pars['pop_scale']       = None      # How much to scale the population
    pars['ms_agent_ratio']  = 10        # Ratio of scale factor of cancer agents to normal agents -- must be an integer
    pars['network']         = 'default' # What type of sexual network to use -- 'random', 'basic', other options TBC
    pars['location']        = 'nigeria' # What location to load data from -- default Nigeria
    pars['lx']              = None      # Proportion of people alive at the beginning of age interval x
    pars['birth_rates']     = None      # Birth rates, loaded below
    pars['death_rates']     = None      # Death rates, loaded below
    pars['rel_birth']       = 1.0       # Birth rate scale factor
    pars['rel_death']       = 1.0       # Death rate scale factor

    # Initialization parameters
    pars['init_hpv_prev'] = sc.dcp(hpd.default_init_prev) # Initial prevalence
    pars['init_hpv_dist'] = None  # Initial type distribution
    pars['rel_init_prev'] = 1.0 # Initial prevalence scale factor

    # Simulation parameters
    pars['start']           = 1995.         # Start of the simulation
    pars['end']             = None          # End of the simulation
    pars['n_years']         = 35            # Number of years to run, if end isn't specified. Note that this includes burn-in
    pars['burnin']          = 25            # Number of years of burnin. NB, this is doesn't affect the start and end dates of the simulation, but it is possible remove these years from plots
    pars['dt']              = 0.25           # Timestep (in years)
    pars['dt_demog']        = 1.0           # Timestep for demographic updates (in years)
    pars['rand_seed']       = 1             # Random seed, if None, don't reset
    pars['verbose']         = hpo.verbose   # Whether or not to display information during the run -- options are 0 (silent), 0.1 (some; default), 1 (default), 2 (everything)
    pars['use_waning']      = False         # Whether or not to use waning immunity. If set to False, immunity from infection and vaccination is assumed to stay at the same level permanently
    pars['use_migration']   = True          # Whether to estimate migration rates to correct the total population size
    pars['model_hiv']       = False         # Whether or not to model HIV natural history
    pars['hiv_pars']        = sc.objdict()  # Can be directly modified by passing in arguments listed in hiv_pars

    # Network parameters, generally initialized after the population has been constructed
    pars['n_clusters']      = 1     # Defines how many clusters (e.g., geospatial) there should be in the simulated population
    pars['cluster_rel_sizes']= None  # Relative sizes of clusters. If None, assign 1/n_clusters to all clusters.
    pars['mixing_steps']    = None  # List of relative mixing weights between clusters by relative distance, length = n_clusters - 1, elements should be [0, 1].
    # E.g, for 3 clusters, mixing_steps=[1,1] means full mixing; mixing_steps = [0, 0] means no between cluster mixing.
    pars['add_mixing']      = None  # Mixing matrix between clusters
    pars['pfa']             = 0     # Switch for partnership formation algorithms; use 0 for small number of clusters, 1 for large number of clusters (e.g., n_clusters/n_agents > 0.05)
    pars['clustered_risk']  = 1     # Strength of relationship between rel_sev and clustering, where 1 means there is no relationship and values above 1 refer to how much more similar clusters are wrt rel_sev
    pars['cluster_rel_sev'] = None  # Array of cluster-specific rel_sev values
    pars['debut']           = dict(f=dict(dist='normal', par1=15.0, par2=2.1), # Location-specific data should be used here if possible
                                   m=dict(dist='normal', par1=17.6, par2=1.8))
    pars['cross_layer']     = 0.05  # Proportion of agents who have concurrent cross-layer relationships
    pars['partners']        = None  # The number of concurrent sexual partners for each partnership type
    pars['acts']            = None  # The number of sexual acts for each partnership type per year
    pars['condoms']         = None  # The proportion of acts in which condoms are used for each partnership type
    pars['layer_probs']     = None  # Proportion of the population in each partnership type
    pars['dur_pship']       = None  # Duration of partnerships in each partnership type
    pars['mixing']          = None  # Mixing matrices for storing age differences in partnerships
    pars['n_partner_types'] = 1  # Number of partnership types - reset below

    # Basic disease transmission parameters
    pars['beta']                = 0.2   # Per-act transmission probability; absolute value, calibrated
    pars['transf2m']            = 1.0   # Relative transmissibility of receptive partners in penile-vaginal intercourse; baseline value
    pars['transm2f']            = 3.69  # Relative transmissibility of insertive partners in penile-vaginal intercourse; based on https://doi.org/10.1038/srep10986: "For vaccination types, the risk of male-to-female transmission was higher than that of female-to-male transmission"
    pars['eff_condoms']         = 0.7   # The efficacy of condoms; https://www.nejm.org/doi/10.1056/NEJMoa053284?url_ver=Z39.88-2003&rfr_id=ori:rid:crossref.org&rfr_dat=cr_pub%20%200www.ncbi.nlm.nih.gov

    # Parameters for disease progression
    pars['hpv_control_prob']    = 0.0 # Probability that HPV is controlled latently vs. cleared
    pars['hpv_reactivation']    = 0.025 # Placeholder; unused unless hpv_control_prob>0
    pars['dur_cancer']          = dict(dist='lognormal', par1=8.0, par2=3.0)  # Duration of untreated invasive cerival cancer before death (years)
    pars['dur_infection_male']  = dict(dist='lognormal', par1=1, par2=1) # Duration of infection for men
    pars['clinical_cutoffs']    = dict(cin1=0.33, cin2=0.676, cin3=0.8) # Parameters used to map disease severity onto cytological grades
    pars['sev_dist']            = dict(dist='normal_pos', par1=1.0, par2=0.25) # Distribution to draw individual level severity scale factors
    pars['age_risk']            = dict(age=30, risk=1)

    # Parameters used to calculate immunity
    pars['imm_init']        = dict(dist='beta_mean', par1=0.35, par2=0.025)  # beta distribution for initial level of immunity following infection clearance. Parameters are mean and variance from https://doi.org/10.1093/infdis/jiv753
    pars['imm_decay']       = dict(form=None)  # decay rate, with half life in years
    pars['cell_imm_init']   = dict(dist='beta_mean', par1=0.25, par2=0.025) # beta distribution for level of immunity against persistence/progression of infection following infection clearance and seroconversion
    pars['imm_boost']       = []  # Multiplicative factor applied to a person's immunity levels if they get reinfected. No data on this, assumption.
    pars['cross_immunity_sus'] = None  # Matrix of susceptibility cross-immunity factors, set by init_immunity() in immunity.py
    pars['cross_immunity_sev'] = None  # Matrix of severity cross-immunity factors, set by init_immunity() in immunity.py
    pars['cross_imm_sus_med']   = 0.3
    pars['cross_imm_sus_high']  = 0.5
    pars['cross_imm_sev_med']   = 0.5
    pars['cross_imm_sev_high']  = 0.7
    pars['own_imm_hr'] = 0.9

    # Genotype parameters
    pars['genotypes']       = [16, 18, 'hi5']  # Genotypes to model
    pars['genotype_pars']   = sc.objdict()  # Can be directly modified by passing in arguments listed in get_genotype_pars

    # Events and interventions
    pars['interventions']   = sc.autolist() # The interventions present in this simulation; populated by the user
    pars['analyzers']       = sc.autolist() # The functions present in this simulation; populated by the user
    pars['timelimit']       = None # Time limit for the simulation (seconds)
    pars['stopping_func']   = None # A function to call to stop the sim partway through

    # Population distribution of the World Standard Population, used to calculate age-standardised rates (ASR) of incidence
    pars['age_bin_edges']        = np.array( [  0,   5,  10,  15,  20,  25,  30,  35,  40,  45,  50,  55,  60,  65,  70,  75,    80,    85, 100])
    pars['standard_pop']    = np.array([pars['age_bin_edges'],
                                        [.12, .10, .09, .09, .08, .08, .06, .06, .06, .06, .05, .04, .04, .03, .02, .01, 0.005, 0.005,   0]])

    # The following variables are stored within the pars dict for ease of access, but should not be directly specified.
    # Rather, they are automatically constructed during sim initialization.
    pars['immunity_map']    = None  # dictionary mapping the index of immune source to the type of immunity (vaccine vs natural)
    pars['imm_kin']         = None  # Constructed during sim initialization using the nab_decay parameters
    pars['genotype_map']    = dict()  # Reverse mapping from number to genotype key
    pars['n_genotypes']     = 1 # The number of genotypes circulating in the population
    pars['n_imm_sources']   = 1 # The number of immunity sources circulating in the population
    pars['vaccine_pars']    = dict()  # Vaccines that are being used; populated during initialization
    pars['vaccine_map']     = dict()  # Reverse mapping from number to vaccine key
    pars['cumdysp']         = dict()

    # Update with any supplied parameter values and generate things that need to be generated
    pars.update(kwargs)
    reset_layer_pars(pars)
    add_mixing(pars) # additional assortative mixing

    return pars


# Define which parameters need to be specified as a dictionary by layer -- define here so it's available at the module level for sim.py
layer_pars = ['partners', 'mixing', 'acts', 'age_act_pars', 'layer_probs', 'dur_pship', 'condoms']


def reset_layer_pars(pars, layer_keys=None, force=False):
    '''
    Helper function to set layer-specific parameters. If layer keys are not provided,
    then set them based on the population type. This function is not usually called
    directly by the user, although it can sometimes be used to fix layer key mismatches
    (i.e. if the contact layers in the population do not match the parameters). More
    commonly, however, mismatches need to be fixed explicitly.

    Args:
        pars (dict): the parameters dictionary
        layer_keys (list): the layer keys of the population, if available
        force (bool): reset the parameters even if they already exist
    '''

    layer_defaults = {}
    # Specify defaults for random -- layer 'a' for 'all'
    layer_defaults['random'] = dict(
        partners    = dict(a=dict(dist='poisson', par1=0.01)), # Everyone in this layer has one partner; this captures *additional* partners. If using a poisson distribution, par1 is roughly equal to the proportion of people with >1 partner
        acts        = dict(a=dict(dist='neg_binomial', par1=100,par2=50)),  # Default number of sexual acts per year for people at sexual peak
        age_act_pars = dict(a=dict(peak=35, retirement=100, debut_ratio=0.5, retirement_ratio=0.1)), # Parameters describing changes in coital frequency over agent lifespans
        layer_probs = dict(a=1.0),  # Default proportion of the population in each layer
        dur_pship   = dict(a=dict(dist='normal_pos', par1=5,par2=3)),    # Default duration of partnerships
        condoms     = dict(a=0.25),  # Default proportion of acts in which condoms are used
    )
    layer_defaults['random']['mixing'], layer_defaults['random']['layer_probs'] = get_mixing('random')

    # Specify defaults for basic sexual network with marital, casual, and one-off partners
    layer_defaults['default'] = dict(
        partners    = dict(m=dict(dist='poisson', par1=0.01), # Everyone in this layer has one marital partner; this captures *additional* marital partners. If using a poisson distribution, par1 is roughly equal to the proportion of people with >1 spouse
                           c=dict(dist='poisson', par1=0.2), # If using a poisson distribution, par1 is roughly equal to the proportion of people with >1 casual partner at a time
                           o=dict(dist='poisson', par1=0.0),), # If using a poisson distribution, par1 is roughly equal to the proportion of people with >1 one-off partner at a time. Can be set to zero since these relationships only last a single timestep
        acts         = dict(m=dict(dist='neg_binomial', par1=80, par2=40), # Default number of acts per year for people at sexual peak
                            c=dict(dist='neg_binomial', par1=10, par2=5), # Default number of acts per year for people at sexual peak
                            o=dict(dist='neg_binomial', par1=1,  par2=.01)),  # Default number of acts per year for people at sexual peak
        age_act_pars = dict(m=dict(peak=30, retirement=100, debut_ratio=0.5, retirement_ratio=0.1), # Parameters describing changes in coital frequency over agent lifespans
                            c=dict(peak=25, retirement=100, debut_ratio=0.5, retirement_ratio=0.1),
                            o=dict(peak=25, retirement=100, debut_ratio=0.5, retirement_ratio=0.1)),
        dur_pship   = dict(m=dict(dist='normal_pos', par1=12, par2=3),
                           c=dict(dist='normal_pos', par1=1, par2=1),
                           o=dict(dist='normal_pos', par1=0.1, par2=0.05)),
        condoms     = dict(m=0.01, c=0.2, o=0.1),  # Default proportion of acts in which condoms are used
    )
    layer_defaults['default']['mixing'], layer_defaults['default']['layer_probs'] = get_mixing('default')

    # Choose the parameter defaults based on the population type, and get the layer keys
    try:
        defaults = layer_defaults[pars['network']]
    except Exception as E:
        errormsg = f'Cannot load defaults for population type "{pars["network"]}"'
        raise ValueError(errormsg) from E
    default_layer_keys = list(defaults['acts'].keys()) # All layers should be the same, but use acts for convenience

    # Actually set the parameters
    for pkey in layer_pars:
        par = {} # Initialize this parameter
        default_val = layer_defaults['random'][pkey]['a'] # Get the default value for this parameter

        # If forcing, we overwrite any existing parameter values
        if force:
            par_dict = defaults[pkey] # Just use defaults
        else:
            par_dict = sc.mergedicts(defaults[pkey], pars.get(pkey, None)) # Use user-supplied parameters if available, else default

        # Figure out what the layer keys for this parameter are (may be different between parameters)
        if layer_keys:
            par_layer_keys = layer_keys # Use supplied layer keys
        else:
            par_layer_keys = list(sc.odict.fromkeys(default_layer_keys + list(par_dict.keys())))  # If not supplied, use the defaults, plus any extra from the par_dict; adapted from https://www.askpython.com/python/remove-duplicate-elements-from-list-python

        # Construct this parameter, layer by layer
        for lkey in par_layer_keys: # Loop over layers
            par[lkey] = par_dict.get(lkey, default_val) # Get the value for this layer if available, else use the default for random
        pars[pkey] = par # Save this parameter to the dictionary

    # Finally, update the number of partnership types
    pars['n_partner_types'] = len(par_layer_keys)

    return


def get_births_deaths(location, verbose=1, by_sex=True, overall=False, die=True):
    '''
    Get mortality and fertility data by location if provided, or use default

    Args:
        location (str):  location
        verbose (bool):  whether to print progress
        by_sex   (bool): whether to get sex-specific death rates (default true)
        overall  (bool): whether to get overall values ie not disaggregated by sex (default false)

    Returns:
        lx (dict): dictionary keyed by sex, storing arrays of lx - the number of people who survive to age x
        birth_rates (arr): array of crude birth rates by year
    '''

    if verbose:
        print(f'Loading location-specific demographic data for "{location}"')
    try:
        death_rates = hpdata.get_death_rates(location=location, by_sex=by_sex, overall=overall)
        birth_rates = hpdata.get_birth_rates(location=location)
        return birth_rates, death_rates
    except ValueError as E:
        warnmsg = f'Could not load demographic data for requested location "{location}" ({str(E)})'
        hpm.warn(warnmsg, die=die)


#%% Genotype/immunity parameters and functions

def get_genotype_choices():
    '''
    Define valid genotype names
    '''
    # List of choices available
    choices = {
        'hpv16':    ['hpv16', '16'],
        'hpv18':    ['hpv18', '18'],
        'hi5':      ['hi5hpv', 'hi5hpv', 'cross-protective'],
        'ohr':      ['ohrhpv', 'non-cross-protective'],
        'hr':       ['allhr', 'allhrhpv', 'hrhpv', 'oncogenic', 'hr10', 'hi10'],
        'lo':       ['lohpv'],
    }
    mapping = {name:key for key,synonyms in choices.items() for name in synonyms} # Flip from key:value to value:key
    return choices, mapping

def get_vaccine_choices():
    '''
    Define valid pre-defined vaccine names
    '''
    # List of choices currently available: new ones can be added to the list along with their aliases
    choices = {
        'default': ['default', None],
        'bivalent':  ['bivalent', 'hpv2', 'cervarix'],
        'quadrivalent': ['quadrivalent', 'hpv4', 'gardasil'],
        'nonavalent': ['nonavalent', 'hpv9', 'cervarix9'],
    }
    dose_1_options = ['1dose', '1doses', '1_dose', '1_doses', 'single_dose']
    dose_2_options = ['2dose', '2doses', '2_dose', '2_doses', 'double_dose']
    dose_3_options = ['3dose', '3doses', '3_dose', '3_doses', 'triple_dose']

    choices['bivalent_2dose'] = [f'{x}_{dose}' for x in choices['bivalent'] for dose in dose_2_options]
    choices['bivalent_3dose'] = [f'{x}_{dose}' for x in choices['bivalent'] for dose in dose_3_options]
    choices['bivalent'] = ['bivalent']+[f'{x}_{dose}' for x in choices['bivalent'] for dose in dose_1_options]
    choices['quadrivalent_2dose'] = [f'{x}_{dose}' for x in choices['quadrivalent'] for dose in dose_2_options]
    choices['quadrivalent_3dose'] = [f'{x}_{dose}' for x in choices['quadrivalent'] for dose in dose_3_options]
    choices['quadrivalent'] = ['quadrivalent']+[f'{x}_{dose}' for x in choices['quadrivalent'] for dose in dose_1_options]
    choices['nonavalent_2dose'] = [f'{x}_{dose}' for x in choices['nonavalent'] for dose in dose_2_options]
    choices['nonavalent_3dose'] = [f'{x}_{dose}' for x in choices['nonavalent'] for dose in dose_3_options]
    choices['nonavalent'] = ['nonavalent']+[f'{x}_{dose}' for x in choices['nonavalent'] for dose in dose_1_options]

    mapping = {name:key for key,synonyms in choices.items() for name in synonyms} # Flip from key:value to value:key
    return choices, mapping


def _get_from_pars(pars, default=False, key=None, defaultkey='default'):
    ''' Helper function to get the right output from genotype functions '''

    # If a string was provided, interpret it as a key and swap
    if isinstance(default, str):
        key, default = default, key

    # Handle output
    if key is not None:
        try:
            return pars[key]
        except Exception as E:
            errormsg = f'Key "{key}" not found; choices are: {sc.strjoin(pars.keys())}'
            raise sc.KeyNotFoundError(errormsg) from E
    elif default:
        return pars[defaultkey]
    else:
        return pars


def get_genotype_pars(default=False, genotype=None):
    '''
    Define the default parameters for the different genotypes
    '''

    pars = sc.objdict()

    pars.hpv16 = sc.objdict()
    pars.hpv16.dur_precin       = dict(dist='normal_pos', par1=0.5, par2=0.25)  # Duration of infection prior to precancer
    pars.hpv16.dur_episomal     = dict(dist='lognormal', par1=2, par2=5) # Duration of episomal infection prior to cancer
    pars.hpv16.sev_fn           = dict(form='logf2', k=0.175, x_infl=0, ttc=30) # Function mapping duration of infection to severity
    pars.hpv16.rel_beta         = 1.0  # Baseline relative transmissibility, other genotypes are relative to this
    pars.hpv16.transform_prob   = 1.3e-9 # Annual rate of transformed cell invading
    pars.hpv16.sev_integral     = 'analytic' # Type of integral used for translating severity to transformation probability. Accepts numeric, analytic, or None
    pars.hpv16.sero_prob        = 0.75 # https://www.sciencedirect.com/science/article/pii/S2666679022000027#fig1

    pars.hpv18 = sc.objdict()
    pars.hpv18.dur_precin       = dict(dist='normal_pos', par1=0.5, par2=0.25)  # Duration of infection prior to precancer
    pars.hpv18.dur_episomal     = dict(dist='lognormal', par1=2, par2=5) # Duration of infection prior to cancer
    pars.hpv18.sev_fn           = dict(form='logf2', k=0.15, x_infl=0, ttc=30) # Function mapping duration of infection to severity
    pars.hpv18.rel_beta         = 0.75  # Relative transmissibility, current estimate from Harvard model calibration of m2f tx
    pars.hpv18.transform_prob   = 1.0e-9 # Annual rate of transformed cell invading
    pars.hpv18.sev_integral     = 'analytic' # Type of integral used for translating severity to transformation probability. Accepts numeric, analytic, or None
    pars.hpv18.sero_prob        = 0.56 # https://www.sciencedirect.com/science/article/pii/S2666679022000027#fig1

    # High-risk oncogenic types included in 9valent vaccine: 31, 33, 45, 52, 58
    pars.hi5 = sc.objdict()
    pars.hi5.dur_precin         = dict(dist='normal_pos', par1=0.5, par2=0.25)  # Duration of infection prior to precancer
    pars.hi5.dur_episomal       = dict(dist='lognormal', par1=2, par2=4) # Duration of infection prior to cancer
    pars.hi5.sev_fn             = dict(form='logf2', k=0.125, x_infl=0, ttc=30) # Function mapping duration of infection to severity
    pars.hi5.rel_beta           = 0.9 # placeholder
    pars.hi5.transform_prob     = 3e-10 # Annual rate of transformed cell invading
    pars.hi5.sev_integral       = 'analytic' # Type of integral used for translating severity to transformation probability. Accepts numeric, analytic, or None
    pars.hi5.sero_prob          = 0.60 # placeholder

    # Other high-risk: oncogenic but not covered in 9valent vaccine: 35, 39, 51, 56, 59
    pars.ohr = sc.objdict()
    pars.ohr.dur_precin         = dict(dist='normal_pos', par1=0.5, par2=0.25)  # Duration of infection prior to precancer
    pars.ohr.dur_episomal       = dict(dist='lognormal', par1=2, par2=6) # Duration of infection prior to cancer
    pars.ohr.sev_fn             = dict(form='logf2', k=0.125, x_infl=0, ttc=30) # Function mapping duration of infection to severity
    pars.ohr.rel_beta           = 0.9 # placeholder
    pars.ohr.transform_prob     = 3e-10 # Annual rate of transformed cell invading
    pars.ohr.sev_integral       = 'analytic' # Type of integral used for translating severity to transformation probability. Accepts numeric, analytic, or None
    pars.ohr.sero_prob          = 0.60 # placeholder

    # All other high-risk types: 31, 33, 35, 39, 45, 51, 52, 56, 58, 59
    # Warning: this should not be used in conjuction with hi5 or ohr
    pars.hr = sc.objdict()
    pars.hr.dur_precin       = dict(dist='normal_pos', par1=0.5, par2=0.25)  # Duration of infection prior to precancer
    pars.hr.dur_episomal     = dict(dist='lognormal', par1=2, par2=4) # Duration of infection prior to cancer
    pars.hr.sev_fn           = dict(form='logf2', k=0.125, x_infl=0, ttc=30) # Function mapping duration of infection to severity
    pars.hr.rel_beta         = 0.9 # placeholder
    pars.hr.transform_prob   = 3e-10 # Annual rate of transformed cell invading
    pars.hr.sev_integral     = 'analytic' # Type of integral used for translating severity to transformation probability. Accepts numeric, analytic, or None
    pars.hr.sero_prob        = 0.60 # placeholder

    # Low-risk
    pars.lr = sc.objdict()
    pars.lr.dur_precin          = dict(dist='normal_pos', par1=0.5, par2=0.25)  # Duration of infection prior to precancer
    pars.lr.dur_episomal        = dict(dist='lognormal', par1=2, par2=4) # Duration of infection prior to cancer
    pars.lr.sev_fn              = dict(form='logf2', k=0.0, x_infl=0, ttc=30) # Function mapping duration of infection to severity
    pars.lr.rel_beta            = 0.9 # placeholder
    pars.lr.transform_prob      = 0 # Annual rate of transformed cell invading
    pars.lr.sev_integral        = 'analytic' # Type of integral used for translating severity to transformation probability. Accepts numeric, analytic, or None
    pars.lr.sero_prob           = 0.60 # placeholder

    return _get_from_pars(pars, default, key=genotype, defaultkey='hpv16')


def get_cross_immunity(cross_imm_med=None, cross_imm_high=None, own_imm_hr=None, default=False, genotype=None):
    '''
    Get the cross immunity between each genotype in a sim
    '''
    pars = dict(
        # All values based roughly on https://academic.oup.com/jnci/article/112/10/1030/5753954 or assumptions
        hpv16 = dict(
            hpv16=1.0, # Default for own-immunity
            hpv18=cross_imm_high,
            hi5=cross_imm_med,
            ohr=cross_imm_med,
            hr=cross_imm_med,
            lr=cross_imm_med,
        ),

        hpv18 = dict(
            hpv16=cross_imm_high,
            hpv18=1.0,  # Default for own-immunity
            hi5=cross_imm_med,
            ohr=cross_imm_med,
            hr=cross_imm_med,
            lr=cross_imm_med,
        ),

        hi5=dict(
            hpv16=cross_imm_med,
            hpv18=cross_imm_med,
            hi5=own_imm_hr,
            ohr=cross_imm_med,
            hr=cross_imm_med,
            lr=cross_imm_med,
        ),

        ohr=dict(
            hpv16=cross_imm_med,
            hpv18=cross_imm_med,
            hi5=cross_imm_med,
            ohr=own_imm_hr,
            hr=cross_imm_med,
            lr=cross_imm_med,
        ),

        lr=dict(
            hpv16=cross_imm_med,
            hpv18=cross_imm_med,
            hi5=cross_imm_med,
            ohr=cross_imm_med,
            hr=cross_imm_med,
            lr=own_imm_hr,
        ),

    )

    return _get_from_pars(pars, default, key=genotype, defaultkey='hpv16')


def get_mixing(network=None):
    '''
    Define defaults for sexual mixing matrices and the proportion of people of each age group
    who have relationships of each type.

    The mixing matrices represent males in the rows and females in the columns.
    Non-zero entires mean that there are some relationships between males/females of the age
    bands in the row/column combination. Entries >1 or <1 can be used to represent relative
    likelihoods of males of a given age cohort partnering with females of that cohort.
    For example, a mixing matrix like the following would mean that males aged 15-30 were twice
    likely to partner with females of age 15-30 compared to females aged 30-50.
        mixing = np.array([
                                #15, 30,
                            [15,  2, 1],
                            [30,  1, 1]])
    Note that the first column of the mixing matrix represents the age bins. The same age bins
    must be used for males and females, i.e. the matrix must be square.

    The proportion of people of each age group who have relationships of each type is
    given by the layer_probs array. The first row represents the age bins, the second row
    represents the proportion of females of each age who have relationships of each type, and
    the third row represents the proportion of males of each age who have relationships of
    each type.
    '''

    if network == 'default':

        mixing = dict(
            m=np.array([
            #       0,  5,  10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75
            [ 0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [ 5,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [10,    0,  0, .1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [15,    0,  0, .1, .1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [20,    0,  0, .1, .1, .1, .1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [25,    0,  0, .5, .1, .5 ,.1, .1,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [30,    0,  0,  1, .5, .5, .5, .5, .1,  0,  0,  0,  0,  0,  0,  0,  0],
            [35,    0,  0, .5,  1,  1, .5,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0],
            [40,    0,  0,  0, .5,  1,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0],
            [45,    0,  0,  0,  0, .1,  1,  1,  2,  1,  1, .5,  0,  0,  0,  0,  0],
            [50,    0,  0,  0,  0,  0, .1,  1,  1,  1,  1,  2, .5,  0,  0,  0,  0],
            [55,    0,  0,  0,  0,  0,  0, .1,  1,  1,  1,  1,  2, .5,  0,  0,  0],
            [60,    0,  0,  0,  0,  0,  0,  0, .1, .5,  1,  1,  1,  2, .5,  0,  0],
            [65,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  2, .5,  0],
            [70,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1, .5],
            [75,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1],
        ]),
            c=np.array([
            #       0,  5,  10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75
            [ 0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [ 5,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [10,    0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [15,    0,  0,  1,  1,  1,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [20,    0,  0,  1,  1,  1,  1,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [25,    0,  0, .5,  1,  1,  1,  1,  1,  0,  0,  0,  0,  0,  0,  0,  0],
            [30,    0,  0,  0, .5,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0],
            [35,    0,  0,  0, .5,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0],
            [40,    0,  0,  0,  0, .5,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0],
            [45,    0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0],
            [50,    0,  0,  0,  0,  0, .5,  1,  1,  1,  1,  1, .5,  0,  0,  0,  0],
            [55,    0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0,  0],
            [60,    0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0],
            [65,    0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  2, .5,  0],
            [70,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5],
            [75,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1],
        ]),
            o=np.array([
            #       0,  5,  10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75
            [ 0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [ 5,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [10,    0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [15,    0,  0,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [20,    0,  0, .5,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [25,    0,  0,  0,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [30,    0,  0,  0,  0,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0],
            [35,    0,  0,  0,  0,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0],
            [40,    0,  0,  0,  0,  0,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0],
            [45,    0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0],
            [50,    0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0,  0,  0],
            [55,    0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0,  0],
            [60,    0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0],
            [65,    0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  2, .5,  0],
            [70,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5],
            [75,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1],
        ]),
        )

        layer_probs = dict(
            m=np.array([
                [ 0,  5,    10,    15,   20,   25,   30,   35,    40,    45,    50,   55,   60,   65,   70,   75],
                [ 0,  0,  0.04,   0.1,  0.1,  0.5,  0.6,  0.7,  0.75,  0.65,  0.55,  0.4,  0.4,  0.4,  0.4,  0.4], # Share of females of each age who are actively seeking marriage if underpartnered
                [ 1,  1,     1,     1,    1,    1,    1,    1,     1,     1,     1,    1,    1,    1,    1,    1]] # Share of males of each age who are actively seeking marriage if underpartnered
            ),
            c=np.array([
                [ 0,  5,    10,    15,   20,   25,   30,   35,    40,    45,    50,   55,   60,   65,   70,   75],
                [ 0,  0,  0.10,   0.7,  0.8,  0.6,  0.6,  0.4,   0.1,  0.05,  0.001, 0.001, 0.001, 0.001, 0.001, 0.001], # Share of females of each age actively seeking casual relationships if underpartnered
                [ 1,  1,     1,     1,    1,    1,    1,    1,     1,     1,     1,    1,    1,    1,    1,    1]] # Share of males of each age actively seeking casual relationships if underpartnered
            ),
            o=np.array([
                [ 0,  5,    10,    15,   20,   25,   30,   35,    40,    45,    50,   55,   60,   65,   70,   75],
                [ 0,  0,  0.01,  0.05, 0.05, 0.04, 0.03, 0.02,  0.01,  0.01,  0.01, 0.01, 0.01, 0.01, 0.01, 0.01], # Share of females of each age actively seeking one-off relationships if underpartnered
                [ 1,  1,     1,     1,    1,    1,    1,    1,     1,     1,     1,    1,    1,    1,    1,    1]] # Share of males of each age actively seeking one-off relationships if underpartnered
            ),
        )

    elif network == 'random':
        mixing = dict(
            a=np.array([
            #       0,  5,  10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75
            [ 0,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [ 5,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [10,    0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [15,    0,  0,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [20,    0,  0, .5,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [25,    0,  0,  0,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0,  0],
            [30,    0,  0,  0,  0,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0,  0],
            [35,    0,  0,  0,  0,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0,  0],
            [40,    0,  0,  0,  0,  0,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0,  0],
            [45,    0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0,  0,  0,  0],
            [50,    0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0,  0,  0],
            [55,    0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0,  0],
            [60,    0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5,  0,  0],
            [65,    0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  2, .5,  0],
            [70,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1, .5],
            [75,    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1],
        ])
        )
        layer_probs = dict(
            a=np.array([
                [ 0,  5,    10,    15,   20,   25,   30,   35,    40,    45,    50,   55,   60,   65,   70,   75],
                [ 0,  0,  0.04,   0.2,  0.6,  0.8,  0.8,  0.8,  0.75,  0.65,  0.55,  0.4,  0.4,  0.4,  0.4,  0.4], # Share of females of each age who are married
                [ 0,  0,  0.01,  0.01,  0.2,  0.6,  0.8,  0.9,  0.90,  0.90,  0.90,  0.8,  0.7,  0.6,  0.5,  0.6]] # Share of males of each age who are married
            ))

    else:
        errormsg = f'Network "{network}" not found; the choices at this stage are random and default.'
        raise ValueError(errormsg)

    return mixing, layer_probs



def get_vaccine_dose_pars(default=False, vaccine=None):
    '''
    Define the parameters for each vaccine
    '''

    pars = dict(

        default = dict(
            imm_init  = dict(dist='beta', par1=30, par2=2), # Initial distribution of immunity
            doses     = 1, # Number of doses for this vaccine
            interval  = None, # Interval between doses
            imm_boost=None,  # For vaccines wiht >1 dose, the factor by which each additional boost increases immunity
        ),

        bivalent = dict(
            imm_init=dict(dist='beta', par1=30, par2=2),  # Initial distribution of immunity
            doses=1,  # Number of doses for this vaccine
            interval=None,  # Interval between doses
            imm_boost=None,  # For vaccines wiht >1 dose, the factor by which each additional boost increases immunity
        ),

        bivalent_2dose = dict(
            imm_init=dict(dist='beta', par1=30, par2=2),  # Initial distribution of immunity
            doses=2,  # Number of doses for this vaccine
            interval=0.5,  # Interval between doses in years
            imm_boost=1.2,  # For vaccines wiht >1 dose, the factor by which each additional boost increases immunity
        ),

        bivalent_3dose = dict(
            imm_init=dict(dist='beta', par1=30, par2=2),  # Initial distribution of immunity
            doses=3,  # Number of doses for this vaccine
            interval=[0.2, 0.5],  # Interval between doses in years
            imm_boost=[1.2, 1.1],  # Factor by which each dose increases immunity
        ),

        quadrivalent = dict(
            imm_init=dict(dist='beta', par1=30, par2=2),  # Initial distribution of immunity
            doses=1,  # Number of doses for this vaccine
            interval=None,  # Interval between doses
            imm_boost=None,  # For vaccines wiht >1 dose, the factor by which each additional boost increases immunity
        ),

        nonavalent = dict(
            imm_init=dict(dist='beta', par1=30, par2=2),  # Initial distribution of immunity
            doses=1,  # Number of doses for this vaccine
            interval=None,  # Interval between doses
            imm_boost=None,  # For vaccines wiht >1 dose, the factor by which each additional boost increases immunity
        ),
    )

    return _get_from_pars(pars, default, key=vaccine)



#%% Methods for computing severity

def compute_severity(t, rel_sev=None, pars=None):
    '''
    Process functional form and parameters into values:
    '''

    pars = sc.dcp(pars)
    form = pars.pop('form')
    choices = [
        'logf2',
        'logf3',
    ]

    # Scale t
    if rel_sev is not None:
        t = rel_sev * t

    # Process inputs
    if form is None or form == 'logf2':
        output = hpu.logf2(t, **pars)

    elif form == 'logf3':
        output = hpu.logf3(t, **pars)

    elif callable(form):
        output = form(t, **pars)

    else:
        errormsg = f'The selected functional form "{form}" is not implemented; choices are: {sc.strjoin(choices)}'
        raise NotImplementedError(errormsg)

    return output


def compute_inv_severity(sev_vals, rel_sev=None, pars=None):
    '''
    Compute time to given severity level given input parameters
    '''

    pars = sc.dcp(pars)
    form = pars.pop('form')
    choices = [
        'logf2',
        'logf3',
    ]

    # Process inputs
    if form is None or form == 'logf2':
        output = hpu.invlogf2(sev_vals, **pars)

    elif form == 'logf3':
        output = hpu.invlogf3(sev_vals, **pars)

    elif callable(form):
        output = form(sev_vals, **pars)

    else:
        errormsg = f'The selected functional form "{form}" is not implemented; choices are: {sc.strjoin(choices)}'
        raise NotImplementedError(errormsg)

    # Scale by relative severity
    if rel_sev is not None:
        output = output / rel_sev

    return output


def compute_severity_integral(t, rel_sev=None, pars=None):
    '''
    Process functional form and parameters into values:
    '''

    pars = sc.dcp(pars)
    form = pars.pop('form')
    choices = [
        'logf2',
        'logf3 with s=1',
    ]

    # Scale t
    if rel_sev is not None:
        t = rel_sev * t

    # Process inputs
    if form is None or form == 'logf2':
        output = hpu.intlogf2(t, **pars)

    elif form=='logf3':
        s = pars.pop('s')
        if s==1:
            output = hpu.intlogf2(t, **pars)
        else:
            errormsg = f'Analytic integral for logf3 only implemented for s=1. Select integral=numeric.'

    else:
        errormsg = f'Analytic integral for the selected functional form "{form}" is not implemented; choices are: {sc.strjoin(choices)}, or select integral=numeric.'
        raise NotImplementedError(errormsg)

    return output

def add_mixing(pars):
    '''
    Create additional mixing matrix
    '''
    cluster_size = pars['n_clusters']

    if 'cluster_rel_sizes' not in pars or pars['cluster_rel_sizes'] is None:
        pars['cluster_rel_sizes'] = np.repeat(1/pars['n_clusters'], pars['n_clusters'])

    if pars['cluster_rel_sizes'].size != pars['n_clusters']:
        errormsg = 'Length of cluster sizes does not match number of clusters'
        raise ValueError(errormsg)

    if cluster_size > 1:
        if 'add_mixing' in pars and pars['add_mixing'] is not None: # If mixing matrix is defined, check if dimension matches n_clusters
            if pars['add_mixing'].shape != (cluster_size, cluster_size):
                errormsg = 'Dimension of input mixing matrix does not match number of clusters'
                raise ValueError(errormsg)
        else: # if mixing matrix is not defined, autogenerate based on mixing_steps
            if 'mixing_steps' not in pars or pars['mixing_steps'] is None:  # if mixing_steps is not supplied, assume well-mixed
                print('Warning: input has clusters with no mixing_steps or mixing matrix. Well-mixed cluster is assumed')
                pars['n_clusters'] = 1
                pars['cluster_rel_sizes'] = np.array([1])
            else:
                if cluster_size < len(pars['mixing_steps']):
                    print('Warning: input has {} mixing steps but only {} clusters.'.format(len(pars['mixing_steps']), cluster_size))
                add_mixing = np.zeros([cluster_size, cluster_size])
                for i, gs in enumerate(pars['mixing_steps'][:cluster_size - 1]):
                    add_mixing += np.diagflat(np.repeat(gs, cluster_size - i - 1), i + 1) # fill the lower diagonal
                add_mixing += add_mixing.T # fill the upper diagonal
                add_mixing[np.diag_indices_from(add_mixing)] = 1  # set diagonal to 1
                pars['add_mixing'] = add_mixing
    if cluster_size == 1:
        pars['add_mixing'] = np.array([[1]])

    if 'sev_dist' in pars:
        rel_sevs = hpu.sample(**pars['sev_dist'], size=cluster_size)
        pars['cluster_rel_sev'] = rel_sevs

    return