from flashy.nuclear import *
from .globals import *
from flashy.yields import getYields, reader, ut
from flashy.utils import x2clog
from matplotlib.patches import Rectangle


class patchN(object):
    def legend_artist(self, legend, orig_handle, fontsize, handlebox):
        x0, y0 = handlebox.xdescent, handlebox.ydescent
        width, height = handlebox.width, handlebox.height
        patch = Rectangle((x0,y0), height, height)
        patch.update_from(orig_handle)
        patch.set_transform(handlebox.get_transform())
        handlebox.add_artist(patch)
        return patch


def fileChemistry(fname, species=[], thresh=1e-6, sprange=[0.0, 0.0], 
                  filetag='chem', show=False, byM=True, 
                  geom='cartesian', direction=[]):
    """Plot yield mass and species from a checkpoint via a lineout.
    
    """
    # ax2 = plt.subplot2grid(layout, (1, 0), aspect="auto", sharex=ax1, sharey=ax1, adjustable='box-forced')
    print(geom, direction)
    t, sp , mss = getYields(fname, geom=geom, direction=direction)
    ad, allsp = reader.getLineout(fname, geom=geom, direction=direction)
    time, _, _, _, paths = reader.getMeta(fname)
    fig = plt.figure(figsize=(9, 9))
    
    layout = (2, 1)
    ax1 = plt.subplot2grid(layout, (0, 0), aspect='auto')
    ax2 = plt.subplot2grid(layout, (1, 0), aspect="auto", adjustable='box-forced')
    #ax3 = plt.subplot2grid(layout, (2, 0), aspect="auto", sharex=ax1, adjustable='box-forced')
    
    ax1.annotate("Time: {:.5f} s".format(time),
                 xy=(0.0, 0.0), xytext=(1.1, 0.95), size=12,
                 textcoords='axes fraction', xycoords='axes fraction')
    ax1.set_ylabel('Total Mass ($M_\odot$)', rotation=90, labelpad=5)
    ax1.set_xlabel('Mass Number (A)')
    ax1.yaxis.set_major_formatter(StrMethodFormatter('{x:.2f}'))
    ax1.yaxis.set_minor_formatter(StrMethodFormatter(''))
    ax1.xaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
    ax1.xaxis.set_minor_formatter(StrMethodFormatter(''))
    
    if not species:
        species = allsp
    spoffset = len(ad)-len(allsp)
    allsp = sortNuclides(allsp)
    styleIter = colIter()
    if byM:
        xs = ut.byMass(ad[0], ad[1])
        ax2.set_xlabel('Mass ($M_{\odot}$)')
    else:
        xs = ad[0]
        ax2.set_xlabel('Radius ($cm$)')
    spnames = []
    for s in range(len(allsp)):
        if allsp[s] not in species:
            continue
        A, sym = elemSplit(allsp[s], invert=True)
        tag = '$^{{{}}}{}$'.format(A, sym)
        spnames.append(sym)
        # p2 to p3: obj.next() > next(obj)
        c, ls = next(styleIter)
        ax1.scatter(A, mss[s], color=c)
        ax2.semilogy(xs, ad[s+spoffset], label=tag, color=c, linestyle=ls, alpha=0.9)
    lgd = ax2.legend(ncol=5, loc='upper left', bbox_to_anchor=(1.0, 1.9), 
      columnspacing=0.0, labelspacing=0.0, markerfirst=True, 
      numpoints=2)
    if sum(sprange)!=0.0:
        ax2.set_xlim(sprange)
    ax2.axhline(1e0, linewidth=1, linestyle=':', color='black')
    ax2.set_ylim(thresh, 2.0)
    ax2.set_ylabel('$X_{i}$', rotation=0, labelpad=10)
    if show:
        plt.tight_layout(pad=1.0, h_pad=0.05, w_pad=0.5, rect=(0, 0, 0.6,1.0))
        return
    else:
        num = paths[1][-5:]
        otpf, _ = os.path.split(paths[0])
        tag = filetag
        savn = '{}{}.png'.format(tag, num)
        savf = os.path.join(otpf, "png")
        savp = os.path.join(otpf, "png", tag, savn)
        # build filetree and save the figure
        if not os.path.exists(savf):
            os.mkdir(savf)
            os.mkdir(os.path.join(savf, tag))
        elif not os.path.exists(os.path.join(savf, tag)):
            os.mkdir(os.path.join(savf, tag))
        plt.tight_layout(pad=1.0, h_pad=0.05, w_pad=0.5, rect=(0, 0, 0.8,1.0))
        plt.savefig(savp,  bbox_extra_artists=(lgd,), bbox_inches='tight')
        plt.close(fig)
        print("Wrote: {}".format(savp))


def plotNuclideGrid(ax, species, xmass=[], z_range=[-0.5,35], n_range=[-0.5,38], 
                    boxsize=1.0, cmmin=1.0e-5, cmmax=1.0, cmap='Blues', 
                    log=False, addtags=True, invert=False):
    """plots a list of species on a grid."""
    cmap = mpl.cm.get_cmap(cmap)
    if len(xmass)>0:
        xis = xmass
    else:
        fakeXi = 1.0-np.random.rand(1)
        xis = [fakeXi[0]]*len(species)
    if invert:
        clr = 'white'
    else:
        clr = 'black'
    nam, zs, ns, As = splitSpecies(species)
    for (z, n, xi) in zip(zs, ns, xis):
        if log:
            square = plt.Rectangle((n-0.5*boxsize, z-0.5*boxsize),
                    boxsize, boxsize, facecolor=cmap(x2clog(xi)),
                    edgecolor=clr)
        else:
            square = plt.Rectangle((n-0.5*boxsize, z-0.5*boxsize),
                    boxsize, boxsize, facecolor=cmap(xi),
                    edgecolor=clr)
        ax.add_patch(square)
        mainsquare = square
    if addtags:
        tags, xs, ys = getNuclideGridNames(list(nam), zs, ns)
        for (t, x, y) in zip(tags, xs, ys):
            ax.text(x, y, t, fontsize=8, verticalalignment='center', 
                    horizontalalignment='right', color=clr)
    #ax.set_ylabel('Z ($p^+$)', color=clr)
    #ax.set_xlabel('N ($n^0$)', color=clr)
    ax.set_ylabel('Proton Number', color=clr)
    ax.set_xlabel('Neutron Number', color=clr)
    ax.set_ylim(z_range)
    ax.set_xlim(n_range)
    #ax.xaxis.tick_top()
    #ax.xaxis.set_label_position('top')
    # remove spines/ticks
    for side in ['bottom','right','top','left']:
        ax.spines[side].set_visible(False)
    ax.set_xticks([]) # labels 
    ax.set_yticks([])
    ax.arrow(0, 12, 0, 10, head_width=0.5, head_length=1, fc=clr, ec=clr)
    ax.arrow(13, 0, 10, 0, head_width=0.5, head_length=1, fc=clr, ec=clr)
    #ax.yaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
    #ax.yaxis.set_minor_formatter(StrMethodFormatter(''))
    #ax.xaxis.set_major_formatter(StrMethodFormatter('{x:.0f}'))
    #ax.xaxis.set_minor_formatter(StrMethodFormatter(''))
    return mainsquare


def plotReaclist(ax, species, rates=[], boxsize=1.0, 
                 cmmin=1.0e-5, cmmax=1.0, cmap='Blues'):
    return 0


def doYouBelieveInMagic(ax, color='brown'):
    """Draws a magical grid of stability (?)"""
    cadabra = [2, 8, 20, 28, 50, 82, 126]
    for abra in cadabra:
        ax.axhline(abra, alpha=0.4, color=color, ls=':')
        p = ax.axvline(abra, alpha=0.4, color=color, ls=':')
    return p


def plotPfac(ax, querym, refname=AGSS09, label='Sun vs Ref',#  ylims=[1e-9, 1],
             norm='Si', offset=6, reftype='solar'):
    """draws abundquery/abundref from a massdict and a filename,
    types of reference are 'solar'(for solar composition) and 'yield' (for other sims)
    returns label and line element for legend"""
    zs, ns, ab = convertYield2Abundance(querym, norm=norm, offset=offset)
    if reftype=='solar':
        zss, nss, solab = readSunComp(refname)
        massF = getMassFractions(nss, solab)
        rescaledsolab = getAbundances(nss, massF, scale=norm, offset=offset)
        soldict = dict(zip(nss, rescaledsolab))
    elif reftype=='yield':
        massdict = readYield(refname)
        zss, nss, solab = convertYield2Abundance(massdict, norm=norm, offset=offset)
        soldict = dict(zip(nss, solab))
    pfacs = []
    for i, n in enumerate(ns):
        if n in soldict:
            pfacs.append((zs[i], n, ab[i]-soldict[n]))
            #pfacs.append((zs[i], n, ab[i]/soldict[n]))
        else:
            print('{} not found in ref.'.format(n))
    x, _, y = zip(*sorted(pfacs))
    ax.axhline(0, ls=':', lw=1, color='green')
    line = ax.plot(x, y, label=label, ls='--', lw=0.5, marker='.', color='black')
    # Prettify
    ax.set_xlabel(u'Atomic Number (Z)')
    ax.set_ylabel('$[X/{}]- [X/{}]_{{ref}}$'.format(norm, norm))
    ax.autoscale()
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:2.0f}'))
    ax.xaxis.set_major_formatter(StrMethodFormatter('{x:2.0f}'))
    return line[0], label


def plotIsoMasses(ax, mdict, label='W7', color='black', ylims=[1e-18, 1.0], notag=False):
    """draws isotopic masses vs atomic mass, returns label and line element for legend"""
    for k in mdict.keys():
        zz = mdict[k]['z']
        vals = []
        for n in mdict[k]['n'].keys():
            vals.append((n+zz, mdict[k]['n'][n]))
        purgevals = [v for v in vals if ylims[0]<= v[1]<=ylims[1]]
        if len(purgevals)==0:
            continue
        xs, ys = zip(*sorted(purgevals))
        line = ax.semilogy(xs, ys, ls='--', lw=0.5, marker='.', label=label, color=color)
        if notag:
            continue
        ax.text(xs[0], ys[0], '${}$'.format(k), color=color,
                size=8, horizontalalignment='right', verticalalignment='bottom',)
    # Prettify
    ax.set_xlabel(u'Atomic Mass (A)')
    ax.set_ylabel('Mass ($M_{\odot}$)')
    ax.set_xlim([-2, 78])
    ax.set_ylim(ylims)
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:0.0e}'))
    ax.xaxis.set_major_formatter(StrMethodFormatter('{x:2.0f}'))
    return line[0], label


def plotAbun(ax, mdict, norm='H', offset=12.0, label='W7', color='black'):
    """draws abundances vs atomic number, returns label and line element for legend"""
    zs, names, mix = convertYield2Abundance(mdict, norm=norm, offset=offset)
    line = ax.plot(zs, mix, color=color, label=label, marker='.', ls=':', lw=1)
    # Prettify
    ax.set_xlabel(u'Atomic Number (Z)')
    ax.set_ylabel('[X/{}] + {:2.1f}'.format(norm, offset))
    #ax.set_xlim([-2, 78])
    #ax.set_ylim(ylims)
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:2.0f}'))
    ax.xaxis.set_major_formatter(StrMethodFormatter('{x:2.0f}'))
    return line[0], label


def speciesGrid(ax, spcodes, yoffset=5.0):
    """draws a grid of the specified species on target ax."""
    Sp, Zs, Ns, As = splitSpecies(spcodes)
    clrs = colIter()
    for i, sp in enumerate(Sp):
        # p2 to p3: obj.next() > next(obj)
        col = next(clrs)[0]
        ax.axvline(Zs[i], alpha=1.0, lw=1, ls='--', c=col)
        ax.text(Zs[i]+0.1, ax.get_ylim()[0]+yoffset, '${}$'.format(sp), color=col, size=10,
                horizontalalignment='left', verticalalignment='bottom')
    return 0


def getNuclideGridNames(names, zs, ns):
    """Retuns tags and positions for a nuclide grid."""
    if 'p' in names and 'H' in names:
        names[names.index('p')] = 'H'  # change proton name to void H tag
    tags = set()
    nams, x, y = [], [], []
    for i, n in enumerate(names):
        if n not in tags:
            tags.add(n)
            nams.append(n)
            x.append(ns[i]-0.7)
            y.append(zs[i])
    return nams, x, y