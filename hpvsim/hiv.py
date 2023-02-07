'''
Defines classes and methods for hiv natural history
'''

import numpy as np
import sciris as sc
import pandas as pd
from collections.abc import Iterable
from . import utils as hpu
from . import defaults as hpd
from . import base as hpb
from .data import loaders as hpdata



class HIVPars(hpb.FlexPretty):
    '''
        A class based around performing operations on a self.pars dict.
        '''

    def __init__(self, pars):
        self.update_pars(pars, create=True)
        return

    def __getitem__(self, key):
        ''' Allow sim['par_name'] instead of sim.pars['par_name'] '''
        try:
            return self.pars[key]
        except:
            all_keys = '\n'.join(list(self.pars.keys()))
            errormsg = f'Key "{key}" not found; available keys:\n{all_keys}'
            raise sc.KeyNotFoundError(errormsg)

    def __setitem__(self, key, value):
        ''' Ditto '''
        if key in self.pars:
            self.pars[key] = value
        else:
            all_keys = '\n'.join(list(self.pars.keys()))
            errormsg = f'Key "{key}" not found; available keys:\n{all_keys}'
            raise sc.KeyNotFoundError(errormsg)
        return

    def update_pars(self, pars=None, create=False):
        '''
        Update internal dict with new pars.

        Args:
            pars (dict): the parameters to update (if None, do nothing)
            create (bool): if create is False, then raise a KeyNotFoundError if the key does not already exist
        '''
        if pars is not None:
            if not isinstance(pars, dict):
                raise TypeError(f'The pars object must be a dict; you supplied a {type(pars)}')
            if not hasattr(self, 'pars'):
                self.pars = pars
            if not create:
                available_keys = list(self.pars.keys())
                mismatches = [key for key in pars.keys() if key not in available_keys]
                if len(mismatches):
                    errormsg = f'Key(s) {mismatches} not found; available keys are {available_keys}'
                    raise sc.KeyNotFoundError(errormsg)
            self.pars.update(pars)
        return

    # %% HIV methods

    def set_hiv_prognoses(self, people, inds, year=None):
        ''' Set HIV outcomes (for now only ART) '''

        art_cov = self['art_adherence']  # Shorten

        # Extract index of current year
        all_years = np.array(list(art_cov.keys()))
        year_ind = sc.findnearest(all_years, year)
        nearest_year = all_years[year_ind]

        # Figure out which age bin people belong to
        age_bins = art_cov[nearest_year][0, :]
        age_inds = np.digitize(people.age[inds], age_bins)

        # Apply ART coverage by age to people
        art_covs = art_cov[nearest_year][1, :]
        art_adherence = art_covs[age_inds]
        people.art_adherence[inds] = art_adherence
        people.rel_sev_infl[inds] = (1-art_adherence)*people.pars['hiv_pars']['rel_hiv_sev_infl']
        people.rel_sus[inds] = (1-art_adherence)*people.pars['hiv_pars']['rel_sus']

        return

    def apply_hiv_rates(self, people, year=None):
        '''
        Apply HIV infection rates to population
        '''
        hiv_pars = self['infection_rates']
        all_years = np.array(list(hiv_pars.keys()))
        year_ind = sc.findnearest(all_years, year)
        nearest_year = all_years[year_ind]
        hiv_year = hiv_pars[nearest_year]
        dt = people.pars['dt']

        hiv_probs = np.zeros(len(people), dtype=hpd.default_float)
        for sk in ['f', 'm']:
            hiv_year_sex = hiv_year[sk]
            age_bins = hiv_year_sex[:, 0]
            hiv_rates = hiv_year_sex[:, 1] * dt
            mf_inds = people.is_female if sk == 'f' else people.is_male
            mf_inds *= people.alive  # Only include people alive
            age_inds = np.digitize(people.age[mf_inds], age_bins)
            hiv_probs[mf_inds] = hiv_rates[age_inds]
        hiv_probs[people.hiv] = 0  # not at risk if already infected

        # Get indices of people who acquire HIV
        hiv_inds = hpu.true(hpu.binomial_arr(hiv_probs))
        people.hiv[hiv_inds] = True

        # Update prognoses for those with HIV
        if len(hiv_inds):

            self.set_hiv_prognoses(people, hiv_inds, year=year)  # Set ART adherence for those with HIV

            for g in range(people.pars['n_genotypes']):
                gpars = people.pars['genotype_pars'][people.pars['genotype_map'][g]]
                hpv_inds = hpu.itruei((people.is_female & people.episomal[g, :]), hiv_inds)  # Women with HIV who have episomal HPV
                if len(hpv_inds):  # Reevaluate these women's severity markers and determine whether they will develop cellular changes
                    people.set_severity_pars(hpv_inds, g, gpars)
                    people.set_severity(hpv_inds, g, gpars, dt)

        return people.scale_flows(hiv_inds)


def get_hiv_data(location=None, hiv_datafile=None, art_datafile=None, verbose=False):
    '''
    Load HIV incidence and art coverage data, if provided
    ART adherance calculations use life expectancy data to infer lifetime average coverage
    rates for people in different age buckets. To give an example, suppose that ART coverage
    over 2010-2020 is given by:
        art_coverage = [0.23,0.3,0.38,0.43,0.48,0.52,0.57,0.61,0.65,0.68,0.72]
    The average ART adherence in 2010 will be higher for younger cohorts than older ones.
    Someone expected to die within a year would be given an average lifetime ART adherence
    value of 0.23, whereas someone expected to survive >10 years would be given a value of 0.506.

    Args:
        location (str): must be provided if you want to run with HIV dynamics
        hiv_datafile (str):  must be provided if you want to run with HIV dynamics
        art_datafile (str):  must be provided if you want to run with HIV dynamics
        verbose (bool):  whether to print progress

    Returns:
        hiv_inc (dict): dictionary keyed by sex, storing arrays of HIV incidence over time by age
        art_cov (dict): dictionary keyed by sex, storing arrays of ART coverage over time by age
        life_expectancy (dict): dictionary storing life expectancy over time by age
    '''

    if hiv_datafile is None and art_datafile is None:
        hiv_incidence_rates, art_adherence = None, None

    else:

        # Load data
        life_exp = get_life_expectancy(location=location,
                                       verbose=verbose)  # Load the life expectancy data (needed for ART adherance calcs)
        df_inc = pd.read_csv(hiv_datafile)  # HIV incidence
        df_art = pd.read_csv(art_datafile)  # ART coverage

        # Process HIV and ART data
        sex_keys = ['Male', 'Female']
        sex_key_map = {'Male': 'm', 'Female': 'f'}

        ## Start with incidence file
        years = df_inc['Year'].unique()
        hiv_incidence_rates = dict()

        # Processing
        for year in years:
            hiv_incidence_rates[year] = dict()
            for sk in sex_keys:
                sk_out = sex_key_map[sk]
                hiv_incidence_rates[year][sk_out] = np.concatenate(
                    [
                        np.array(df_inc[(df_inc['Year'] == year) & (df_inc['Sex'] == sk_out)][['Age', 'Incidence']],
                                 dtype=hpd.default_float),
                        np.array([[150, 0]])  # Add another entry so that all older age groups are covered
                    ]
                )

        # Now compute ART adherence over time/age
        art_adherence = dict()
        years = df_art['Year'].values
        for i, year in enumerate(years):

            # Use the incidence file to determine which age groups we want to calculate ART coverage for
            ages_inc = hiv_incidence_rates[year]['m'][:, 0]  # Read in the age groups we have HIV incidence data for
            ages_ex = life_exp[year]['m'][:, 0]  # Age groups available in life expectancy file
            ages = np.intersect1d(ages_inc, ages_ex)  # Age groups we want to calculate ART coverage for

            # Initialize age-specific ART coverage dict and start filling it in
            cov = np.zeros(len(ages), dtype=hpd.default_float)
            for j, age in enumerate(ages):
                idx = np.where(life_exp[year]['f'][:, 0] == age)[0]  # Finding life expectancy for this age group/year
                this_life_exp = life_exp[year]['f'][idx, 1]  # Pull out value
                last_year = int(year + this_life_exp)  # Figure out the year in which this age cohort is expected to die
                year_ind = sc.findnearest(years,
                                          last_year)  # Get as close to the above year as possible within the data
                if year_ind > i:  # Either take the mean of ART coverage from now up until the year of death
                    cov[j] = np.mean(df_art[i:year_ind]['ART Coverage'].values)
                else:  # Or, just use ART overage in this year
                    cov[j] = df_art.iloc[year_ind]['ART Coverage']

            art_adherence[year] = np.array([ages, cov])

    return hiv_incidence_rates, art_adherence


def get_life_expectancy(location, verbose=False):
    '''
    Get life expectancy data by location
    life_expectancy (dict): dictionary storing life expectancy over time by age
    '''
    if location is not None:
        if verbose:
            print(f'Loading location-specific life expectancy data for "{location}" - needed for HIV runs')
        try:
            life_expectancy = hpdata.get_life_expectancy(location=location)
            return life_expectancy
        except ValueError as E:
            errormsg = f'Could not load HIV data for requested location "{location}" ({str(E)})'
            raise NotImplementedError(errormsg)
    else:
        raise NotImplementedError('Cannot load HIV data without a specified location')