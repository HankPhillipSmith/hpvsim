'''
Tests for single simulations
'''

#%% Imports and settings
import os
import pytest
import sys
import sciris as sc
import numpy as np
import hpvsim as hpv

do_plot = 1
do_save = 0


#%% Define the tests

def test_dynamic_pars():
    sc.heading('Test dynamics pars intervention')

    pars = {
        'pop_size': 10e3,
        'n_years': 10,
    }

    # Model an intervention to increase condom use
    condom_int = hpv.dynamic_pars(
        condoms=dict(timepoints=10, vals={'c': 0.9}))  # Increase condom use among casual partners to 90%

    # Model an intervention to increase the age of sexual debut
    debut_int = hpv.dynamic_pars(
        {'debut': {
            'timepoints': '2020',
            'vals': dict(f=dict(dist='normal', par1=20, par2=2.1), # Increase mean age of sexual debut
                         m=dict(dist='normal', par1=19.6,par2=1.8))
        }
        }
    )

    sim = hpv.Sim(pars=pars, interventions=[condom_int, debut_int])
    sim.run()
    return sim


def test_vaccines(do_plot=False, do_save=False, fig_path=None):
    sc.heading('Test prophylactic vaccine intervention')

    hpv16 = hpv.genotype('HPV16')
    hpv18 = hpv.genotype('HPV18')
    verbose = .1
    debug = 0

    pars = {
        'pop_size': 50e3,
        'n_years': 40,
        'genotypes': [hpv16, hpv18],
        'location': 'tanzania',
        'dt': .2,
    }

    sim = hpv.Sim(pars=pars)
    # Model an intervention to roll out prophylactic vaccination
    vx_prop = 1.0
    def age_subtarget(sim):
        ''' Select people who are eligible for vaccination '''
        inds = sc.findinds((sim.people.age >= 9) & (sim.people.age <=14))
        return {'vals': [vx_prop for _ in inds], 'inds': inds}

    def faster_age_subtarget(sim):
        ''' Select people who are eligible for vaccination '''
        inds = sc.findinds((sim.people.age >= 9) & (sim.people.age <=24))
        return {'vals': [vx_prop for _ in inds], 'inds': inds}
    years = np.arange(sim['burnin'], sim['n_years']-sim['burnin'], dtype=int)
    bivalent_vx = hpv.vaccinate_prob(vaccine='bivalent', label='bivalent, 9-14', timepoints=years,
                                       subtarget=age_subtarget)

    bivalent_vx_faster = hpv.vaccinate_prob(vaccine='bivalent', label='bivalent, 9-24', timepoints=years,
                                       subtarget=faster_age_subtarget)

    n_runs = 3

    # Define the scenarios
    scenarios = {
        'no_vx': {
            'name': 'No vaccination',
            'pars': {
            }
        },
        'vx': {
            'name': f'Vaccinate {vx_prop*100}% of 9-14y girls starting in 2020',
            'pars': {
                'interventions': [bivalent_vx]
            }
        },
        'faster_vx': {
            'name': f'Vaccinate {vx_prop * 100}% of 9-24y girls starting in 2020',
            'pars': {
                'interventions': [bivalent_vx_faster]
            }
        },
    }

    metapars = {'n_runs': n_runs}

    scens = hpv.Scenarios(sim=sim, metapars=metapars, scenarios=scenarios)
    scens.run(verbose=verbose, debug=debug)
    scens.compare()

    if do_plot:
        to_plot = {
            'HPV incidence': [
                'total_hpv_incidence',
            ],
            'CIN prevalence': [
                'total_cin_prevalence',
            ],
            'Cancers per 100,000 women': [
                'total_cancer_incidence',
            ],
        }
        scens.plot(do_save=do_save, to_plot=to_plot, fig_path=fig_path)

    return scens

def test_screening(do_plot=False, do_save=False, fig_path=None):
    sc.heading('Test screening intervention')

    hpv16 = hpv.genotype('HPV16')
    hpv18 = hpv.genotype('HPV18')
    verbose = .1
    debug = 0
    n_agents = 50e3

    pars = {
        'pop_size': n_agents,
        'n_years': 60,
        'burnin': 25,
        'start': 1975,
        'genotypes': [hpv16, hpv18],
        'pop_scale' : 25.2e6 / n_agents,
        'dt': .2,
    }

    # Model an intervention to screen 50% of 30 year olds with hpv DNA testing and treat immediately
    screen_prop = .5
    hpv_screening = hpv.Screening(primary_screen_test='hpv', treatment='ablative', screen_start_age=30,
                                  screen_stop_age=50, screen_interval=10, timepoints='2010',
                                  prob=screen_prop)

    cyto_screening = hpv.Screening(primary_screen_test='cytology', treatment='ablative', screen_start_age=30,
                                  screen_stop_age=50, screen_interval=10, timepoints='2010',
                                  prob=screen_prop)
    # sim = hpv.Sim(pars=pars, interventions = [hpv_screening])
    # sim.run()
    # sim.plot()
    # return sim

    sim = hpv.Sim(pars=pars)
    n_runs = 1

    # Define the scenarios
    scenarios = {
        'no_screening_rsa': {
            'name': 'No screening',
            'pars': {
                'location': 'south africa'
            }
        },
        'hpv_screening': {
            'name': f'Screen {screen_prop * 100}% of 30-50y women with {hpv_screening.label}',
            'pars': {
                'interventions': [hpv_screening],
                'location': 'south africa'
            }
        },
        'cyto_screening': {
            'name': f'Screen {screen_prop * 100}% of 30-50y women with {cyto_screening.label}',
            'pars': {
                'interventions': [cyto_screening],
                'location': 'south africa'
            }
        },
    }

    metapars = {'n_runs': n_runs}

    scens = hpv.Scenarios(sim=sim, metapars=metapars, scenarios=scenarios)
    scens.run(verbose=verbose, debug=debug)
    scens.compare()

    if do_plot:
        to_plot = {
            'HPV prevalence': [
                'total_hpv_prevalence',
            ],
            'CIN prevalence': [
                'total_cin_prevalence',
            ],
            'Cancers per 100,000 women': [
                'total_cancer_incidence',
            ],
        }
        scens.plot(to_plot=to_plot)

    return scens


#%% Run as a script
if __name__ == '__main__':

    # Start timing and optionally enable interactive plotting
    T = sc.tic()

    # sim0 = test_dynamic_pars()
    # scens = test_vaccines(do_plot=True)
    scens = test_screening(do_plot=True)

    sc.toc(T)
    print('Done.')
