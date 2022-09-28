"""
Testing a new algorithm for computing progression probabilities
"""

# Imports
import numpy as np
import sciris as sc
import pandas as pd
import hpvsim as hpv
import hpvsim.utils as hpu
import matplotlib.pyplot as plt
from scipy.stats import lognorm


# Create sim to get baseline prognoses parameters
sim = hpv.Sim(genotypes='all')
sim.initialize()

# Get parameters
ng = sim['n_genotypes']
genotype_pars = sim['genotype_pars']
genotype_map = sim['genotype_map']
cancer_thresh = 0.99

# Prognoses from Harvard model
prognoses = dict(
        duration_cutoffs  = np.array([0,       1,          2,          3,          4,          5,          10]),       # Duration cutoffs (lower limits)
        seroconvert_probs = np.array([0.25,    0.5,        0.95,       1.0,        1.0,        1.0,        1.0]),      # Probability of seroconverting given duration of infection
        cin1_probs        = np.array([0.015,   0.3655,     0.86800,    1.0,        1.0,        1.0,        1.0]),      # Conditional probability of developing CIN1 given HPV infection
        cin2_probs        = np.array([0.020,   0.0287,     0.0305,     0.06427,    0.1659,     0.3011,     0.4483]),   # Conditional probability of developing CIN2 given CIN1, derived from Harvard model calibration
        cin3_probs        = np.array([0.007,   0.0097,     0.0102,     0.0219,     0.0586,     0.112,      0.1779]),   # Conditional probability of developing CIN3 given CIN2, derived from Harvard model calibration
        cancer_probs      = np.array([0.002,   0.003,      0.0564,     0.1569,     0.2908,     0.3111,     0.5586]),   # Conditional probability of developing cancer given CIN3, derived from Harvard model calibration
        )

# Shorten duration names
dur_precin = [genotype_pars[genotype_map[g]]['dur_precin'] for g in range(ng)]
dur_dysp = [genotype_pars[genotype_map[g]]['dur_dysp'] for g in range(ng)]
dysp_rate = [genotype_pars[genotype_map[g]]['dysp_rate'] for g in range(ng)]
prog_time = [genotype_pars[genotype_map[g]]['prog_time'] for g in range(ng)]
prog_rate = [genotype_pars[genotype_map[g]]['prog_rate'] for g in range(ng)]


#%% Helper functions
def lognorm_params(par1, par2):
    """
    Given the mode and std. dev. of the log-normal distribution, this function
    returns the shape and scale parameters for scipy's parameterization of the
    distribution.
    """
    mean = np.log(par1 ** 2 / np.sqrt(par2 ** 2 + par1 ** 2))  # Computes the mean of the underlying normal distribution
    sigma = np.sqrt(np.log(par2 ** 2 / par1 ** 2 + 1))  # Computes sigma for the underlying normal distribution

    scale = np.exp(mean)
    shape = sigma
    return shape, scale


def logf1(x, k):
    '''
    The concave part of a logistic function, with point of inflexion at 0,0
    and upper asymptote at 1. Accepts 1 parameter which determines the growth rate.
    '''
    return (2 / (1 + np.exp(-k * x))) - 1


def logf2(x, x_infl, k):
    '''
    Logistic function, constrained to pass through 0,0 and with upper asymptote
    at 1. Accepts 2 parameters: growth rate and point of inlfexion.
    '''
    l_asymp = -1/(1+np.exp(k*x_infl))
    return l_asymp + 1/( 1 + np.exp(-k*(x-x_infl)))


# Figure settings
font_size = 30
sc.fonts(add=sc.thisdir(aspath=True) / 'Libertinus Sans')
sc.options(font='Libertinus Sans')
plt.rcParams['font.size'] = font_size
colors = sc.gridcolors(ng)
x = np.linspace(0.01, 2, 200)

#%% Preliminary calculations (all to be moved within an analyzer? or sim method?)

###### Share of women who develop of detectable dysplasia by genotype
shares = []
gtypes = []
for g in range(ng):
    sigma, scale = lognorm_params(dur_precin[g]['par1'], dur_precin[g]['par2'])
    rv = lognorm(sigma, 0, scale)
    aa = np.diff(rv.cdf(x))
    bb = logf1(x, dysp_rate[g])[1:]
    shares.append(np.dot(aa, bb))
    gtypes.append(genotype_map[g].upper())


###### Distribution of eventual outcomes for women by genotype
noneshares, cin1shares, cin2shares, cin3shares, cancershares = [], [], [], [], []
longx = np.linspace(0.01, 20, 1000)
for g in range(ng):
    sigma, scale = lognorm_params(dur_dysp[g]['par1'], dur_dysp[g]['par2'])
    rv = lognorm(sigma, 0, scale)
    dd = logf2(longx, prog_time[g], prog_rate[g])

    indcin1 = sc.findinds(dd<.33)[-1]
    if (dd>.33).any():
        indcin2 = sc.findinds((dd>.33)&(dd<.67))[-1]
    else:
        indcin2 = indcin1
    if (dd>.67).any():
        indcin3 = sc.findinds((dd>.67)&(dd<cancer_thresh))[-1]
    else:
        indcin3 = indcin2
    if (dd>cancer_thresh).any():
        indcancer = sc.findinds(dd>cancer_thresh)[-1]
    else:
        indcancer = indcin3

    noneshares.append(1 - shares[g])
    cin1shares.append(((rv.cdf(longx[indcin1])-rv.cdf(longx[0]))*shares[g]))
    cin2shares.append(((rv.cdf(longx[indcin2])-rv.cdf(longx[indcin1]))*shares[g]))
    cin3shares.append(((rv.cdf(longx[indcin3])-rv.cdf(longx[indcin2]))*shares[g]))
    cancershares.append(((rv.cdf(longx[indcancer])-rv.cdf(longx[indcin3]))*shares[g]))

######## Outcomes by duration of infection and genotype
n_samples = 10e3

# create dataframes
data = {}
years = np.arange(1,21)
cin1_shares, cin2_shares, cin3_shares, cancer_shares = [], [], [], []
all_years = []
all_genotypes = []
for g in range(ng):
    sigma, scale = lognorm_params(dur_dysp[g]['par1'], dur_dysp[g]['par2'])
    r = lognorm(sigma, 0, scale)

    for year in years:
        mean_peaks = logf2(year, prog_time[g], prog_rate[g])
        peaks = np.minimum(1, hpu.sample(dist='lognormal', par1=mean_peaks, par2=0.1, size=n_samples))
        cin1_shares.append(sum(peaks<0.33)/n_samples)
        cin2_shares.append(sum((peaks>0.33)&(peaks<0.67))/n_samples)
        cin3_shares.append(sum((peaks>0.67)&(peaks<cancer_thresh))/n_samples)
        cancer_shares.append(sum(peaks>cancer_thresh)/n_samples)
        all_years.append(year)
        all_genotypes.append(genotype_map[g].upper())
data = {'Year':all_years, 'Genotype':all_genotypes, 'CIN1':cin1_shares, 'CIN2':cin2_shares, 'CIN3':cin3_shares, 'Cancer': cancer_shares}
sharesdf = pd.DataFrame(data)


################################################################################
# BEGIN FIGURE 1
################################################################################
def make_fig1():
    fig, ax = plt.subplots(2, 3, figsize=(24, 12))

    ################################################################################
    # Pre-dysplasia dynamics
    ################################################################################

    ###### Distributions
    for g in range(ng):
        sigma, scale = lognorm_params(dur_precin[g]['par1'], dur_precin[g]['par2'])
        rv = lognorm(sigma, 0, scale)
        ax[0,0].plot(x, rv.pdf(x), color=colors[g], lw=2, label=genotype_map[g].upper())
    ax[0,0].legend()
    ax[0,0].set_xlabel("Pre-dysplasia/control duration")
    ax[0,0].set_ylabel("")
    ax[0,0].grid()
    ax[0,0].set_title("Distribution of infection durations\nprior to dysplasia or control")


    ###### Relationship between durations and probability of detectable dysplasia
    xx = prognoses['duration_cutoffs']
    yy = prognoses['cin1_probs']
    for g in range(ng):
        ax[0,1].plot(x, logf1(x, dysp_rate[g]), color=colors[g], lw=2)
    ax[0,1].plot(xx[:-1], yy[:-1], 'ko', label="Values from\nHarvard model")
    ax[0,1].set_xlabel("Pre-dysplasia/control duration")
    ax[0,1].set_ylabel("")
    ax[0,1].grid()
    ax[0,1].legend(fontsize=30, frameon=False)
    ax[0,1].set_title("Probability of developing\ndysplasia by duration")


    ###### Distributions post-dysplasia
    thisx = np.linspace(0.01, 20, 100)
    for g in range(ng):
        sigma, scale = lognorm_params(dur_dysp[g]['par1'], dur_dysp[g]['par2'])
        rv = lognorm(sigma, 0, scale)
        ax[0,2].plot(thisx, rv.pdf(thisx), color=colors[g], lw=2, label=genotype_map[g].upper())
    ax[0,2].set_xlabel("Duration of dysplasia")
    ax[0,2].set_ylabel("")
    ax[0,2].grid()
    ax[0,2].set_title("Distribution of dysplasia durations\nprior to cancer/control")



    ################################################################################
    # Post-dysplasia dynamics
    ################################################################################

    ###### Relationship between durations peak clinical severity
    cmap = plt.cm.Oranges([0.25,0.5,0.75,1])
    n_samples = 10
    for g in range(ng):
        ax[1,0].plot(thisx, logf2(thisx, prog_time[g], prog_rate[g]), color=colors[g], lw=2, label=genotype_map[g].upper())
        # Plot variation
        for year in range(1, 21):
            mean_peaks = logf2(year, prog_time[g], prog_rate[g])
            peaks = np.minimum(1, hpu.sample(dist='lognormal', par1=mean_peaks, par2=0.1, size=n_samples))
            ax[1, 0].plot([year] * n_samples, peaks, color=colors[g], lw=0, marker='o', alpha=0.5)

    ax[1,0].set_xlabel("Duration of dysplasia")
    ax[1,0].set_ylabel("")
    ax[1,0].grid(axis='x')
    ax[1,0].set_title("Mean peak clinical severity")
    ax[1,0].get_yaxis().set_ticks([])
    ax[1,0].axhline(y=0.33, ls=':', c='k')
    ax[1,0].axhline(y=0.67, ls=':', c='k')
    ax[1,0].axhline(y=cancer_thresh, ls=':', c='k')
    ax[1,0].axhspan(0, 0.33, color=cmap[0],alpha=.4)
    ax[1,0].axhspan(0.33, 0.67, color=cmap[1],alpha=.4)
    ax[1,0].axhspan(0.67, cancer_thresh, color=cmap[2],alpha=.4)
    ax[1,0].axhspan(cancer_thresh, 1, color=cmap[3],alpha=.4)
    ax[1,0].text(-0.3, 0.08, 'CIN1', fontsize=30, rotation=90)
    ax[1,0].text(-0.3, 0.4, 'CIN2', fontsize=30, rotation=90)
    ax[1,0].text(-0.3, 0.73, 'CIN3', fontsize=30, rotation=90)

    ###### Share of women who develop each CIN grade
    loc_array = np.array([-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,1,2,3,4,5,6,7,8,9,10])
    w = 0.04
    for y in years:
        la = loc_array[y - 1] * w + np.sign(loc_array[y - 1])*(-1)*w/2
        bottom = np.zeros(3)
        for gn, grade in enumerate(['CIN1', 'CIN2', 'CIN3', 'Cancer']):
            ydata = sharesdf[sharesdf['Year']==y][grade]
            ax[1,1].bar(np.arange(1,ng+1)+la, ydata, width=w, color=cmap[gn], bottom=bottom, edgecolor='k', label=grade);
            bottom = bottom + ydata

    # ax[1,1].legend()
    ax[1,1].set_title("Share of women with dysplasia\nby clinical grade and duration")
    ax[1,1].set_xlabel("")
    ax[1,1].set_xticks(np.arange(ng) + 1)
    ax[1,1].set_xticklabels(gtypes)


    ##### Final outcomes for women
    bottom = np.zeros(ng+1)
    all_shares = [noneshares+[sum([j*.33 for j in noneshares])],
                  cin1shares+[sum([j*.33 for j in cin1shares])],
                  cin2shares+[sum([j*.33 for j in cin2shares])],
                  cin3shares+[sum([j*.33 for j in cin3shares])],
                  cancershares+[sum([j*.33 for j in cancershares])],
                  ]
    for gn,grade in enumerate(['None', 'CIN1', 'CIN2', 'CIN3', 'Cancer']):
        ydata = np.array(all_shares[gn])
        if len(ydata.shape)>1: ydata = ydata[:,0]
        color = cmap[gn-1] if gn>0 else 'gray'
        ax[1,2].bar(np.arange(1,ng+2), ydata, color=color, bottom=bottom, label=grade)
        bottom = bottom + ydata
    ax[1,2].set_xticks(np.arange(ng+1) + 1)
    ax[1,2].set_xticklabels(gtypes+['Average'])
    ax[1,2].set_ylabel("")
    ax[1,2].set_title("Eventual outcomes for women\n")
    ax[1,2].legend(bbox_to_anchor =(1.2, 1.),loc='upper center',fontsize=30,ncol=1,frameon=False)

    fig.tight_layout()
    plt.savefig("progressions-1.png", dpi=100)


################################################################################
# BEGIN FIGURE 2
################################################################################
def make_fig2():
    fig, ax = plt.subplots(1, 3, figsize=(24, 8))


    fig.tight_layout()
    plt.savefig("progressions-2.png", dpi=100)


#%% Run as a script
if __name__ == '__main__':

    T = sc.tic()

    make_fig1()
    # make_fig2()

    sc.toc(T)
    print('Done.')
