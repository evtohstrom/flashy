import pandas as pd
from .IOutils import cl, np, fortParse, os, _cdxfolder, getTITANtime, writePBSscript
from .utils import cart2sph
_FLASHdefaults = 'setup_params'
_otpfolder = 'chk'
pd.set_option('display.max_colwidth', 0)

class parGroup(object):
    def __setattr__(self, att, val):
        if hasattr(self, att):
            comp = getattr(self, att)
            if isinstance(comp, dict):  # here were at a defaults obj (values are dicts)
                if isinstance(val, dict):  # init/overwriting a value
                    super().__setattr__(att, val)
                else:  # setting the value field
                    comp['value'] = val
                    super().__setattr__(att, comp)
            else:  # this is a param obj (only keys and values)
                super().__setattr__(att, val)
        else:  # new att, initialize
            super().__setattr__(att, val)
    
    def __init__(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)
    
    def update(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)
            
    def items(self):
        keys = self.__dict__
        values = [getattr(self, att) for att in keys]
        return zip(keys, values)


class parameterGroup(object):
    def __init__(self, parfile):
        # fillcode is a workaround to avoid creating empty parGroups.
        self.meta = getMeta(parfile)
        if not self.meta['code']:
            dc = makeParDict(parfile)
            self.params = parGroup(dc)
        elif self.meta['code']==1:
            dc = readSetupParams(parfile)
            self.defaults = parGroup(dc)
        else:
            dc = makeParDict(parfile)
            self.params = parGroup(dc)
            dc = readSetupParams(os.path.join(self.meta['cdxpath'], _FLASHdefaults))
            self.defaults = parGroup(dc)
            self.mergeValues()

    def setPars(self, parfile):
        """sets the parameters from a file in the object."""
        newmeta = getMeta(parfile)
        if newmeta['default']:  # add or update defaults
            if not self.meta['code']:
                self.defaults = readSetupParams(parfile)
                self.meta = newmeta
            else:
                self.defaults.update(readSetupParams(parfile))
        else:  # overwrite params (safer)
            self.params = parGroup(makeParDict(parfile))
            if self.meta['code']:
                self.mergeValues()
    
    def purgeGroup(self):
        """clears default value fields and removes self.params"""
        if self.meta['code']==0:
            print('Erasing params.')
            self.params = parGroup({})
        elif self.meta['code']==1:
            print('Clearing defaults.')
            for k, v in self.defaults.items():
                setattr(self.defaults, k, '')
        else:
            print('Clearing parameterGroup')
            self.params = parGroup({})
            for k, v in self.params.items():
                setattr(self.defaults, k, '')
    
    def mergeValues(self):
        """adds parameter values to the defaults dictionary."""
        if not self.defaults or not self.params:
            print('flashy.parameterGroup: Params-Defaults pair not found. Returning.')
            return 1
        else:
            for k, v in self.params.items():
                setattr(self.defaults, k, fortParse(v, dec=False))
            self.meta['code'] = 2
    
    def tabulate(self, allpars=False):
        if not self.meta['code']:  # return params
            A = pd.DataFrame(list(self.params.items()), columns=['Parameter', 'Value'])
            return A.set_index('Parameter')
        elif self.meta['code']==1 or allpars:  # return defaults
            A = pd.DataFrame(dict(self.defaults.items()))
        else:  # return 'docked' params
            try:
                docked = [z for z in self.defaults.items() if len(str(z[1]['value']))>0]
            except TypeError:
                print('parGroup.tabulate.error: string index error in docked.'\
                      ' flash.par includes unknown params to simulation.')
                return pd.DataFrame()
            A = pd.DataFrame(dict(docked))
        A = A.transpose()
        A.index.name = 'Parameter'
        if 'comment' in A.columns:
            return A[['value', 'default', 'family', 'comment']]
        else:
            return A

    def getStyledTable(self, stylerprops={}, tableprops={}):
        #if not stylerprops:
        #    stylerprops = {'background-color':'#111111', 'color': '#dbe1ea'}
        #if not tableprops:
        #    tableprops = {'selector':"tr:hover", 'props':[("background-color", '#6f5757')]}
        if self.meta['code']==0:
            print('No defaults found, returning params only')
            A = self.tabulate()
            return A.style
        elif self.meta['code']==1:
            print('No set values, returning defaults')
            A = self.tabulate()
            return A.style
        else:
            A = self.tabulate(allpars=True)
            S = A.style
            #S.set_properties(**stylerprops)
            #S.set_table_styles([tableprops])
            redind = A.index[A['value']!=A['default']].tolist()
            S.applymap(stylerTest, subset=pd.IndexSlice[redind, ['value']])
            return S

    def writeParfile(self, outfile='', terse=False):
        if outfile:
            outpath = os.path.abspath(outfile)
            print(outpath)
            try:
                docked = [z for z in self.defaults.items() if len(str(z[1]['value']))>0]
                writeDictionary(dict(docked), outpath, meta=True, terse=terse)
            except Exception as e:
                print('Failed to write documentation, writing params only.')
                writeDictionary(dict(self.params.items()), outpath, meta=False)
            print('Wrote: {}'.format(outpath))
        else:  # default is to assume 'docked' params and write to runfolder/otp
            self.vuvuzela()
            docked = [z for z in self.defaults.items() if len(str(z[1]['value']))>0]
            cdx = self.meta['cdxpath']
            cpname = os.path.join(cdx, 'flash.par')
            writeDictionary(dict(docked), os.path.abspath(cpname), meta=True, terse=terse)
            print('Wrote: {}'.format(cpname))
            # create checkpoint folder
            otpf = self.defaults.output_directory['value']
            outpath = os.path.join(cdx, otpf)
            os.makedirs(outpath, exist_ok=True)
            # write flash.par to runfolder
            otpf = "../{}/".format(self.meta['runname'])
            outpath = os.path.join(cdx, otpf)
            cpname = os.path.join(outpath, 'flash.par')
            writeDictionary(dict(docked), os.path.abspath(cpname), meta=True, terse=terse)
            print('Wrote: {}'.format(cpname))

    def vuvuzela(self):
        """Sound the horn of ERROR."""
        dkeys = [z[0] for z in self.defaults.items() if len(str(z[1]['value']))>0]
        geom = self.defaults.geometry
        if self.meta['geometry']!=geom['value']:
            print("BZZZZZZZZZZZZ: GEOMETRY DOESN'T MATCH: "\
                  "setup:{} parfile:{}".format(self.meta['geometry'], geom['value']))
        for k in getEssential(self.meta['dimension']):
            if k not in dkeys:
                print("BZZZZZZZZZZZZ: {} NOT SET!".format(k))

    def readMeta(self):
        """returns dimension, cells per block, and maxblocks from a 'docked' parfile"""
        dim = int(self.meta['dimension'])
        cells = self.meta['cells'].split('x')
        cells[-1] = cells[-1].replace('cells', '')
        cells = list(map(int, cells))
        maxblocks = float(self.meta['maxblocks'].replace('maxb',''))
        return dim, cells, maxblocks

    def readEssential(self):
        """returns nblocks, minima, and maxima from a 'docked' parfile"""
        dim = int(self.meta['dimension'])
        keys = getEssential(dim)
        step = int(len(keys)/dim)
        nblocks = [getattr(self.defaults, k)['value'] for k in keys[0::step]]
        mins = [getattr(self.defaults, k)['value'] for k in keys[1::step]]
        maxs = [getattr(self.defaults, k)['value'] for k in keys[2::step]]
        return [float(n) for n in nblocks], [float(m) for m in mins], [float(m) for m in maxs]
    
    def probeSimulation(self, frac=0.4, forcePEs=0, verbose=True):
        dim, cells, maxbl = self.readMeta()
        nblocks, mins, maxs = self.readEssential()
        area, tblcks, tcells = 1.0, 1.0, 1.0
        rmax = float(self.defaults.lrefine_max['value'])
        sotp = []
        for i in range(dim):
            dname = {0:'x', 1:'y', 2:'z'}[i]
            span = maxs[i]-mins[i]
            limblcks = np.power(2, (rmax-1))*float(nblocks[i])
            limcells = limblcks*cells[i]
            #minspan = span/limcells
            sotp.append('{} span: {:2.4E}, resolution: {:2.4E}'.format(dname, span, span/limcells))
            #area*=span
            tblcks*=limblcks
            tcells*=limcells
            # print(limblcks, limcells)
        
        # mult(spans)/mult(nblocks)/mult(cells)/2^(ref-1)/2^(ref-1) = area of cell
        # ref 1 is nblocks, therefore ref-1

        sotp.append('Max Refinement: {:0.0f}'.format(rmax))
        #sotp.append('Resolution: {:E}'.format(np.sqrt(area/tcells)))  # this is not correct
        sotp.append('Maximum cells: {:E}'.format(tcells))
        sotp.append('Maximum Blocks: {:E}'.format(tblcks))
        sotp.append('Max Blocks per PE: {:0.0f}'.format(maxbl))
        if forcePEs:
            sotp.append('forced PEs: {:0.0f}'.format(forcePEs))
            nodes = forcePEs
        else:
            maxPEs = tblcks/maxbl
            sotp.append('Maximum PEs: {:0.0f}'.format(maxPEs))
            sotp.append('Optimistic alloc ({:.0%}): {:0.2f}'.format(frac, maxPEs*frac))
            nodes = int(maxPEs*frac)+1
        if verbose:
            print('\n'.join(sotp))
        return nodes, sotp
    
    def writeRunFiles(self, frac=0.4, forcePEs=0, terse=True, multisub=True, prefix='', IOwindow=120):
        """Probes the parameters, sets up required resources, and writes 
        necessary files based on a stringent structure.
        
        Args:
            frac(float): reduce allocation by frac.
            terse(bool): add descriptions to parameters in the par file.
            multisub(bool): activate iterator (see flashy.IOutils).
            prefix(str): pass a prefix to runname generator.
            IOwindow(int): seconds to extract from walltime to write Checkpoints.
            
        """
        # sets otp_directory and runname key in meta
        self.generateRunName(prefix=prefix)
        # estimate allocation
        nodes, _ = self.probeSimulation(frac=frac,  forcePEs=forcePEs)
        time = getTITANtime(nodes)
        inputs = np.array([float(x) for x in time.split(':')])
        factrs = np.array([3600.0, 60.0, 1.0])
        seconds = sum(inputs*factrs) - IOwindow  # time for last checkpoint
        self.defaults.wall_clock_time_limit = int(seconds)

        # write parfiles in both cdx and otp folders 
        self.writeParfile(terse=terse)
        # write submit script at otp folder
        auxpath = '../{}/'.format(self.meta['runname'])
        outpath = os.path.join(self.meta['cdxpath'], auxpath)
        subpath = os.path.join(outpath, '{}.pbs'.format(self.meta['runname']))
        self.writeSubmit(subpath, nodes=nodes, time=time, j1=False, multisub=multisub)
        return subpath
    
    def writeSubmit(self, submitpath, j1=False, time='02:00:00', 
                    nodes=16, ompth=16, multisub=True):
        qsubfold, qsubname = os.path.split(submitpath)
        runf = os.path.abspath(self.meta['cdxpath'])
        otpf = self.defaults.output_directory['value']
        auxf = '../{}'.format(self.meta['runname'])
        code = []
        # move where the action is and get the corresponding flash.par
        code.append('cd {}'.format(runf))
        code.append('cp {} .'.format(os.path.join(auxf, 'flash.par')))
        if multisub:
            nendestimate = self.defaults.tmax['value']/self.defaults.checkpointFileIntervalTime['value']
            # export chaining arguments and apply iterator to set the file number
            code.append('export QSUBFOLD={}'.format(os.path.abspath(qsubfold)))
            code.append('export QSUBNAME={}'.format(qsubname))
            code.append('bash iterator {} flash.par {}'.format(otpf, int(nendestimate)))
            code.append('wait')
        if self.meta['dimension'] > 1:
            if nodes>512:  # heed the warnings, set limit to 512
                code.append('lfs setstripe -c 512 {}'.format(os.path.join(otpf)))
            else:
                code.append('lfs setstripe -c {} {}'.format(nodes, os.path.join(otpf)))
        if j1:
            nodes*=2
            ompth = 8
            code.append('aprun -n{} -d{} -j1 ./flash4 &'.format(nodes, ompth))
        else:
            code.append('aprun -n{} -d{} ./flash4 &'.format(nodes, ompth))
        if multisub:
            code.append('wait')
            code.append('cd $QSUBFOLD')
            code.append('qsub $QSUBNAME')
        code.append('wait')
        pbsins = ['#PBS -o {}'.format(os.path.join(runf, auxf))]
        writePBSscript(submitpath, code, pbsins=pbsins, time=time, nodes=nodes, ompth=ompth,
                       proj='csc198', mail='rivas.aguilera@gmail.com',abe='a')
        print('Wrote: {}'.format(submitpath))
        
    def generateRunName(self, prefix=''):
        if not prefix:
            prefix = getProfilePrefix(self.defaults.initialWDFile['value'])
        match = (self.defaults.x_match['value'], 
                 self.defaults.y_match['value'], 
                 self.defaults.z_match['value'])
        direc = cart2sph(*match)
        rout, rin = self.defaults.r_match_outer['value'], self.defaults.r_match_inner['value']
        size = rout-rin
        dim = self.meta['dimension']
        if sum(direc)==0.0:
            prefix += '_ring{}'.format(int(self.defaults.r_match_inner['value']/1e5))
        elif dim==3:
            prefix += '_point{}_{}_{}'.format(int(direc[0]/1e5), int(direc[1]), int(direc[2]))
        elif dim==2:  # 2D is x-y, not x-z as in canonical spherical, hence direc[2]
            prefix += '_point{}_{}'.format(int(direc[0]/1e5), int(direc[2]))
        else:
            prefix += '_point{}'.format(int(direc[0]/1e5))
        temp = self.defaults.t_ignite_outer['value']
        runname = '{}_ms{}_t{:.1f}'.format(prefix, int(size/1e5), temp/1e9)
        print ('Run name generated: {}'.format(runname))
        self.defaults.geometry = self.meta['geometry']
        # separate auxiliary files from checkpoints to stripe otp folder.
        self.meta['runname'] = runname
        self.defaults.output_directory = "../{}/{}/".format(runname, _otpfolder)
        self.defaults.log_file = "../{}/run.log".format(runname)
        self.defaults.stats_file = "../{}/stats.dat".format(runname)

    # qgrid-df methods, deprecated
    def readChanges(self, df):
        # turn df to a simple dictionary
        if 'comment' in df.columns:
            pars, values = list(df.index), list(df['value'])
            newpdict = dict(zip(pars, values))
        else:
            newpdict = df.T.to_dict("records")[0]
        # parse values to avoid 'int'
        parsedv = [fortParse(str(x), dec=False) for x in newpdict.values()]
        self.params.update(dict(zip(newpdict.keys(), parsedv)))
        # refresh docked values and remove empty value parameters for when retabulating.
        self.mergeValues()


def getProfilePrefix(string):
    """returns a prefix for a runfolder from a given profile filename
    profile format: wdSource_shellSource_mass_shellmass.dat
    
    """
    profilename = os.path.basename(string[:-4])
    wd, shell, wdm, shm = profilename.split('_')
    code = wd[0]+shell[0]
    mass = getFloat(wdm)
    shma = getFloat(shm)
    return '{}_m{:.0f}_sh{:.0f}'.format(code, mass*1e3, shma*1e3)


def getFloat(string):
    """returns rightmost float in a string."""
    for i in range(len(string)):
        try:
            val = float(string[i:])
            return val
        except ValueError:
            continue
    return 0.0


def stylerTest(value):
    """stub to change colors in selected cells."""
    return 'color: #ec971f'


def getMeta(filepath):
    """Infer required properties of the run from runfolder name 
    created by the method flashy.setupFLASH.
    """
    path, file = os.path.split(filepath)
    # path is either ../runcode/cdx or ../runcode/otp_***
    runpath, fldr = os.path.split(path)
    _, runname = os.path.split(runpath)
    meta = {}
    meta['cdxpath'] = os.path.join(runpath, _cdxfolder)
    deffile = os.path.join(meta['cdxpath'], _FLASHdefaults)
    if file==_FLASHdefaults:
        meta['default'] = 1
        meta['code'] = 1  # read only defaults
    elif os.path.isfile(deffile):
        meta['default'] = 0
        meta['code'] = 2  # read both params and defaults
    else:
        meta['default'] = 0
        meta['code'] = 0  # read only params
    try:
        net, geom, cells, maxblocks = runname.split('.')
    except Exception as e:
        return meta
    dimension = len(cells.split('x'))
    keys = ['network', 'geometry', 'cells', 'maxblocks', 'dimension']
    newkeys = dict(zip(keys, [net, geom, cells, maxblocks, dimension]))
    meta.update(newkeys)
    return meta


def readSetupParams(filename):
    pardict = {}
    setp = {}
    comment = []
    try:
        for line in reversed(open(filename).readlines()):
            if line.startswith('        '):
                comment.append(line.strip())
            elif not line.startswith((' ', '\n')):
                fam = line.strip('\n ')
                for k in pardict.keys():
                    pardict[k]['family'] = fam
                setp.update(pardict)
                pardict = {}
            elif line.startswith('    '):
                par = line.strip().split()[0]
                pardict[par] = {}
                pardict[par]['value'] = ""
                defa = line.strip().split('[')[-1].strip(' ]')
                pardict[par]['default'] = fortParse(defa)
                pardict[par]['comment'] = " ".join(reversed(comment))
                comment = []
    except FileNotFoundError:
        print('paramSetup.readSetupParams: Defaults file not found, returning empty dict.')
        pass  # return an empty dictionary
    return setp


def makeParDict(parfile):
    """ get a dictionary of parameters from a flash.par file"""
    pars = []
    with open(parfile, 'r') as par:
        for line in par:
            l = line.strip('\n')
            if l.startswith('#'):
                continue
            elif '=' in l:
                lsplit = l.split('=')
                # get name of parameter (left of '=')
                p = lsplit[0].strip()
                # remove comment from value (right of '=')
                v = lsplit[1].split('#')[0].strip()
                pars.append((p,v))
    return dict(pars)


def getEssential(dim):
    """Returns parsed names for essential parameters in a simulation.
    Bleeding edge of inference here, careful with changing order of 
    variables...
    
    """
    dnames = {1:['x'], 2:['x', 'y'], 3:['x', 'y', 'z']}[dim]
    keys = []
    for dn in dnames:        
        line = 'nblock{0},{0}min,{0}max,'\
               '{0}l_boundary_type,{0}r_boundary_type'.format(dn)
        keys += line.split(',')
    return keys


def getListedDefs(supradict):
    """split a defaults dictionary into arrays."""
    pars, vals, defs, docs, fams = [], [], [], [], []
    for par in supradict.keys():
        pars.append(par)
        docs.append(supradict[par]['comment'])
        vals.append(supradict[par]['value'])
        defs.append(supradict[par]['default'])
        fams.append(supradict[par]['family'])
    return pars, vals, defs, docs, fams


def writeDictionary(indict, outfile, meta=False, terse=False):
    """write a formatted parameter list to a file."""
    if meta:
        ps, vs, ds, dcs, fms = getListedDefs(indict)
        dat = list(zip(ps,vs,ds,dcs,fms))
        sorted(dat, key=lambda x: x[4])
        groups = sorted(set(fms))
        with open(outfile, 'w') as o:
            for g in groups:
                o.write("\n##### {} #####\n\n".format(g))
                vals = [x for x in dat if x[4]==g]
                maxlen = max([len(x[0]) for x in vals])
                for (p, v, d, dc, fm) in sorted(vals):
                    if terse:
                        o.write("{:{length}} = {} # {} \n".format(p, fortParse(str(v)), d, length=maxlen))
                    else:
                        o.write("{:{length}} = {} # {} {}\n".format(p, fortParse(str(v)), d, dc, length=maxlen))
    else:
        maxlen = max([len(x) for x in indict.keys()])
        with open(outfile, 'w') as o:
            for key, val in sorted(indict.items()):
                o.write("{:{pal}} = {:}\n".format(key, fortParse(str(val)), pal=maxlen))

