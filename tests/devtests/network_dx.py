'''
Tests for network options (geostructure and diagnostic visualizations)
'''

#%% Imports and settings
import sciris as sc
import numpy as np
import hpvsim as hpv
import matplotlib.pyplot as plt
import pylab as pl
import pandas as pd
import seaborn as sns

do_plot = 1
do_save = 0
base_pars = {
    'n_agents': 2e4,
    'start': 1970,
    'end': 2020,
    'location': 'nigeria'
}

#%% Network analyzer

class new_pairs_snap(hpv.Analyzer):
    # analyzer for recording new partnerships of each timestep
    def __init__(self, start_year=None, **kwargs):
        super().__init__(**kwargs)
        self.new_pairs = pd.DataFrame(columns = ['f', 'm', 'acts', 'dur', 'start', 'end', 'age_f', 'age_m', 'year', 'rtype', 'cluster'])
        self.start_year = start_year
        self.yearvec = None

    def initialize(self, sim):
        super().initialize()
        self.yearvec = sim.yearvec
        if self.start_year is None:
            self.start_year = sim['start']

    def apply(self, sim):
        if sim.yearvec[sim.t] >= self.start_year:
            tind = sim.yearvec[sim.t] - sim['start']
            for rtype in ['m','c','o']:
                new_rship_inds = (sim.people.contacts[rtype]['start'] == tind).nonzero()[0]
                if len(new_rship_inds):
                    contacts = pd.DataFrame.from_dict(sim.people.contacts[rtype].get_inds(new_rship_inds))
                    #contacts = pd.DataFrame.from_dict(sim.people.contacts[rtype])
                    contacts['year'] = int(sim.yearvec[sim.t])
                    contacts['rtype'] = rtype
                    self.new_pairs = pd.concat([self.new_pairs, contacts])
        return

def run_network(clusters, mixing_steps, start, end, pop, labels):
    snap = hpv.snapshot(
        timepoints=['1990', '2000', '2010', '2020'],
    )
    snaps = []
    new_pairs = new_pairs_snap(start_year = 2012)
    df_new_pairs = pd.DataFrame(columns = ['f', 'm', 'acts', 'dur', 'start', 'end', 'age_f', 'age_m', 'year', 'rtype', 'cluster', 'sim'])
    fig0, axes = pl.subplots(2, 1)
    for i, (n_clusters, mixing) in enumerate(zip(clusters, mixing_steps)):
        pars = dict(
            n_agents=pop,
            start=start,
            end=end,
            location='nigeria',
            ms_agent_ratio=100,
            n_clusters=n_clusters,
            #clustered_risk=risk,
            mixing_steps = mixing,
            #pfa = 1,
            #random_pairing=True,
            analyzers=[snap, new_pairs]
        )

        sim = hpv.Sim(pars=pars)
        sim.run()
        layer_keys = sim.people.layer_keys()
        num_layers = len(layer_keys)
        # Plot age mixing
        labels += ['{} cluster, {} mixing steps'.format(n_clusters, len(mixing))]
        snaps.append(sim.get_analyzer('snapshot'))
        new_pairs_snaps = sim.get_analyzer('new_pairs_snap').new_pairs
        new_pairs_snaps['sim'] = i
        df_new_pairs = pd.concat([df_new_pairs, new_pairs_snaps])
        plot_mixing(df_new_pairs, layer_keys)
        axes[0].plot(sim.results['year'], sim.results['infections'], label=labels[i])
        axes[1].plot(sim.results['year'], sim.results['cancers'])
    axes[0].legend()
    axes[0].set_ylabel('Infections')
    axes[1].set_ylabel('Cancers')
    fig0.show()

    fig, axes = pl.subplots(nrows=i+1, ncols=num_layers, figsize=(14, 10), sharey='col')
    font_size = 15
    pl.rcParams['font.size'] = font_size
    for i, isnap in enumerate(snaps):
        people = isnap.snapshots[-1] # snapshot from 2020
        rships_f = np.zeros((num_layers, len(people.age_bin_edges)))
        rships_m = np.zeros((num_layers, len(people.age_bin_edges)))
        age_bins = np.digitize(people.age, bins=people.age_bin_edges) - 1
        n_rships = people.n_rships
        for lk, lkey in enumerate(layer_keys):
            for ab in np.unique(age_bins):
                inds_f = (age_bins==ab) & people.is_female
                inds_m = (age_bins==ab) & people.is_male
                rships_f[lk,ab] = n_rships[lk,inds_f].mean()
                rships_m[lk, ab] = n_rships[lk, inds_m].mean()
            ax = axes[i, lk]
            yy_f = rships_f[lk,:]
            yy_m = rships_m[lk,:]
            ax.bar(people.age_bin_edges-1, yy_f, width=1.5, label='Female')
            ax.bar(people.age_bin_edges+1, yy_m, width=1.5, label='Male')
            ax.set_xlabel(f'Age')
            ax.set_title(f'Average number of relationships, {lkey}')
        axes[i, 0].set_ylabel(labels[i])
    axes[0,2].legend()
    fig.tight_layout()
    fig.show()


def cluster_demo():
    sc.heading('Cluster test')
    # Default: well-mixed (1 cluster)
    sim0 = hpv.Sim(pars=base_pars)
    assert sim0['n_clusters'] == 1
    # Multiple clusters
    pars1 = base_pars
    pars1['n_clusters'] = 10
    pars1['mixing_steps'] = np.repeat(1,9)
    sim1 = hpv.Sim(pars=pars1)
    print(sim1['add_mixing'])
    # Modifying mixing steps
    pars2 = pars1
    pars2['mixing_steps'] = [0.5, 0.01] # diagonal is 1 by default, set relative mixing at 0.5 for adjacent clusters, 0.01 for clusters with distance = 2
    sim2 = hpv.Sim(pars=pars2)
    print(sim2['add_mixing'])


def network_demo():
    clusters = [10, 10]
    mixing_steps = [np.ones(9), [0.9,0.5,0.1]]
    start = 1970
    end = 2020
    pop = 2e4
    labels = ['status quo', 'clustered']

    sims = []
    snap = hpv.snapshot(
        timepoints=['1990', '2000', '2010', '2020'],
    )
    new_pairs = new_pairs_snap(start_year = 2012)
    for n_clusters, mixing, label in zip(clusters, mixing_steps, labels):
        pars = dict(
            n_agents=pop,
            start=start,
            end=end,
            location='nigeria',
            ms_agent_ratio=100,
            n_clusters=n_clusters,
            mixing_steps=mixing,
            analyzers=[snap, new_pairs]
        )
        sim = hpv.Sim(pars=pars, label=label)
        sims.append(sim)
    msim = hpv.MultiSim(sims)
    msim.run()
    msim.plot(style='simple')
    plt.show()

    # plot age and cluster mixing patterns for each sim
    for sim in msim.sims:
        plot_mixing(sim, 'age')
        plot_mixing(sim, 'cluster')

    # plot number of relationships overtime


def plot_mixing(sim, dim):
    df_new_pairs = sim.get_analyzer('new_pairs_snap').new_pairs
    if dim == 'age':
        bins = np.linspace(0, 75, 16, dtype=int)
        bins = np.append(bins, 100)
        df_new_pairs['x_bins'] = pd.cut(df_new_pairs['age_f'], bins)
        df_new_pairs['y_bins'] = pd.cut(df_new_pairs['age_m'], bins)
    elif dim == 'cluster':
        df_new_pairs['x_bins'] = df_new_pairs['cluster_f']
        df_new_pairs['y_bins'] = df_new_pairs['cluster_m']

    count_df = df_new_pairs.groupby(['rtype', 'year', 'x_bins', 'y_bins']).size().reset_index(name='count')
    def facet(data, **kwargs):
        data = data.pivot(index='x_bins', columns='y_bins', values='count')
        ax = sns.heatmap(data, **kwargs)
        ax.invert_yaxis()
    g = sns.FacetGrid(count_df, col='year', row='rtype', height=4)
    g.map_dataframe(facet, cmap='viridis', cbar=True, square=True)
    g.set_axis_labels(f'{dim} of female partners', f'{dim} of male partners')
    g.fig.subplots_adjust(top=0.9)
    g.fig.suptitle(sim.label)
    g.tight_layout()
    plt.show()

def plot_rships():
    fig, axes = pl.subplots(nrows=i+1, ncols=num_layers, figsize=(14, 10), sharey='col')
    font_size = 15
    pl.rcParams['font.size'] = font_size
    for i, isnap in enumerate(snaps):
        people = isnap.snapshots[-1] # snapshot from 2020
        rships_f = np.zeros((num_layers, len(people.age_bin_edges)))
        rships_m = np.zeros((num_layers, len(people.age_bin_edges)))
        age_bins = np.digitize(people.age, bins=people.age_bin_edges) - 1
        n_rships = people.n_rships
        for lk, lkey in enumerate(layer_keys):
            for ab in np.unique(age_bins):
                inds_f = (age_bins==ab) & people.is_female
                inds_m = (age_bins==ab) & people.is_male
                rships_f[lk,ab] = n_rships[lk,inds_f].mean()
                rships_m[lk, ab] = n_rships[lk, inds_m].mean()
            ax = axes[i, lk]
            yy_f = rships_f[lk,:]
            yy_m = rships_m[lk,:]
            ax.bar(people.age_bin_edges-1, yy_f, width=1.5, label='Female')
            ax.bar(people.age_bin_edges+1, yy_m, width=1.5, label='Male')
            ax.set_xlabel(f'Age')
            ax.set_title(f'Average number of relationships, {lkey}')
        axes[i, 0].set_ylabel(labels[i])
    axes[0,2].legend()
    fig.tight_layout()
    fig.show()

#%% Run as a script
if __name__ == '__main__':

    T = sc.tic()
    network_demo()
    #cluster_demo()
    sc.toc(T)
    print('Done.')