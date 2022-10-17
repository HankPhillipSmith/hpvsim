'''
Define options for hpvsim, mostly plotting options. All options should
be set using set() or directly, e.g.::

    hp.options(font_size=18)

To reset default options, use::

    hp.options('default')

Note: "options" is used to refer to the choices available (e.g., DPI), while "settings"
is used to refer to the choices made (e.g., DPI=150).
'''

import os
import pylab as pl
import sciris as sc
import matplotlib.font_manager as fm

# Only the class instance is public
__all__ = ['options']


#%% General settings


# Define simple plotting options -- similar to Matplotlib default
rc_simple = {
    'axes.axisbelow':    True, # So grids show up behind
    'axes.spines.right': False,
    'axes.spines.top':   False,
    'figure.facecolor':  'white',
    'font.family':       'sans-serif', # Replaced with Mulish in load_fonts() if import succeeds
    'legend.frameon':    False,
}

# Define default plotting options -- based on Seaborn
rc_hpvsim = sc.mergedicts(rc_simple, {
    'axes.facecolor': '#f2f2ff',
    'axes.grid':      True,
    'grid.color':     'white',
    'grid.linewidth': 1,
})


#%% Define the options class

class Options(sc.objdict):
    '''
    Set options for hpvsim.

    Use ``hp.options.set('defaults')`` to reset all values to default, or ``hp.options.set(dpi='default')``
    to reset one parameter to default. See ``hp.options.help(detailed=True)`` for
    more information.

    Options can also be saved and loaded using ``hp.options.save()`` and ``hp.options.load()``.
    See ``hp.options.context()`` and ``hp.options.with_style()`` to set options
    temporarily.

    Common options are (see also ``hp.options.help(detailed=True)``):

        - verbose:        default verbosity for simulations to use
        - style:          the plotting style to use
        - dpi:            the overall DPI (i.e. size) of the figures
        - font:           the font family/face used for the plots
        - fontsize:       the font size used for the plots
        - interactive:    convenience method to set show, close, and backend
        - jupyter:        defaults for Jupyter (change backend and figure close/return)
        - show:           whether to show figures
        - close:          whether to close the figures
        - backend:        which Matplotlib backend to use
        - warnings:       how to handle warnings (e.g. print, raise as errors, ignore)

    **Examples**::

        hp.options(dpi=150) # Larger size
        hp.options(style='simple', font='Rosario') # Change to the "simple" hpvsim style with a custom font
        hp.options.set(fontsize=18, show=False, backend='agg', precision=64) # Multiple changes
        hp.options(interactive=False) # Turn off interactive plots
        hp.options(jupyter=True) # Defaults for Jupyter
        hp.options('defaults') # Reset to default options

    '''

    def __init__(self):
        super().__init__()
        optdesc, options = self.get_orig_options() # Get the options
        self.update(options) # Update this object with them
        self.setattribute('optdesc', optdesc) # Set the description as an attribute, not a dict entry
        self.setattribute('orig_options', sc.dcp(options)) # Copy the default options
        return


    def __call__(self, *args, **kwargs):
        '''Allow ``hp.options(dpi=150)`` instead of ``hp.options.set(dpi=150)`` '''
        return self.set(*args, **kwargs)


    def to_dict(self):
        ''' Pull out only the settings from the options object '''
        return {k:v for k,v in self.items()}


    def __repr__(self):
        ''' Brief representation '''
        output = sc.objectid(self)
        output += 'hpvsim options (see also hp.options.disp()):\n'
        output += sc.pp(self.to_dict(), output=True)
        return output


    def __enter__(self):
        ''' Allow to be used in a with block '''
        return self


    def __exit__(self, *args, **kwargs):
        ''' Allow to be used in a with block '''
        try:
            reset = {}
            for k,v in self.on_entry.items():
                if self[k] != v: # Only reset settings that have changed
                    reset[k] = v
            self.set(**reset)
            self.delattribute('on_entry')
        except AttributeError as E:
            errormsg = 'Please use hp.options.context() if using a with block'
            raise AttributeError(errormsg) from E
        return


    def disp(self):
        ''' Detailed representation '''
        output = 'hpvsim options (see also hp.options.help()):\n'
        keylen = 10 # Maximum key length  -- "interactive"
        for k,v in self.items():
            keystr = sc.colorize(f'  {k:>{keylen}s}: ', fg='cyan', output=True)
            reprstr = sc.pp(v, output=True)
            reprstr = sc.indent(n=keylen+4, text=reprstr, width=None)
            output += f'{keystr}{reprstr}'
        print(output)
        return


    @staticmethod
    def get_orig_options():
        '''
        Set the default options for hpvsim -- not to be called by the user, use
        ``hp.options.set('defaults')`` instead.
        '''

        # Options acts like a class, but is actually an objdict for simplicity
        optdesc = sc.objdict() # Help for the options
        options = sc.objdict() # The options

        optdesc.verbose = 'Set default level of verbosity (i.e. logging detail): e.g., 0.1 is an update every 10 simulated timesteps'
        options.verbose = float(os.getenv('HPVSIM_VERBOSE', 0.1))

        optdesc.style = 'Set the default plotting style -- options are "hpvsim" and "simple" plus those in pl.style.available; see also options.rc'
        options.style = os.getenv('HPVSIM_STYLE', 'hpvsim')

        optdesc.dpi = 'Set the default DPI -- the larger this is, the larger the figures will be'
        options.dpi = int(os.getenv('HPVSIM_DPI', pl.rcParams['figure.dpi']))

        optdesc.font = 'Set the default font family (e.g., sans-serif or Arial)'
        options.font = os.getenv('HPVSIM_FONT', pl.rcParams['font.family'])

        optdesc.fontsize = 'Set the default font size'
        options.fontsize = int(os.getenv('HPVSIM_FONT_SIZE', pl.rcParams['font.size']))

        optdesc.interactive = 'Convenience method to set figure backend, showing, and closing behavior'
        options.interactive = os.getenv('HPVSIM_INTERACTIVE', True)

        optdesc.jupyter = 'Convenience method to set common settings for Jupyter notebooks: set to "retina" or "widget" (default) to set backend'
        options.jupyter = os.getenv('HPVSIM_JUPYTER', False)

        optdesc.show = 'Set whether or not to show figures (i.e. call pl.show() automatically)'
        options.show = int(os.getenv('HPVSIM_SHOW', True))

        optdesc.close = 'Set whether or not to close figures (i.e. call pl.close() automatically)'
        options.close = int(os.getenv('HPVSIM_CLOSE', False))

        optdesc.returnfig = 'Set whether or not to return figures from plotting functions'
        options.returnfig = int(os.getenv('COVASIM_RETURNFIG', True))

        optdesc.backend = 'Set the Matplotlib backend (use "agg" for non-interactive)'
        options.backend = os.getenv('HPVSIM_BACKEND', pl.get_backend())

        optdesc.rc = 'Matplotlib rc (run control) style parameters used during plotting -- usually set automatically by "style" option'
        options.rc = sc.dcp(rc_hpvsim)

        optdesc.warnings = 'How warnings are handled: options are "warn" (default), "print", and "error"'
        options.warnings = str(os.getenv('HPVSIM_WARNINGS', 'warn'))

        optdesc.sep = 'Set thousands seperator for text output'
        options.sep = str(os.getenv('HPVSIM_SEP', ','))

        optdesc.precision = 'Set arithmetic precision -- 32-bit by default for efficiency'
        options.precision = int(os.getenv('HPVSIM_PRECISION', 32))

        return optdesc, options


    def set(self, key=None, value=None, **kwargs):
        '''
        Actually change the style. See ``hp.options.help()`` for more information.

        Args:
            key    (str):    the parameter to modify, or 'defaults' to reset everything to default values
            value  (varies): the value to specify; use None or 'default' to reset to default
            kwargs (dict):   if supplied, set multiple key-value pairs

        **Example**::

            hp.options.set(dpi=50) # Equivalent to hp.options(dpi=50)
        '''

        reload_required = False

        # Reset to defaults
        if key in ['default', 'defaults']:
            kwargs = self.orig_options # Reset everything to default

        # Handle other keys
        elif key is not None:
            kwargs = sc.mergedicts(kwargs, {key:value})

        # Handle Jupyter
        if 'jupyter' in kwargs.keys() and kwargs['jupyter']:
            jupyter = kwargs['jupyter']
            kwargs['returnfig'] = False # We almost never want to return figs from Jupyter, since then they appear twice
            try: # This makes plots much nicer, but isn't available on all systems
                if not os.environ.get('SPHINX_BUILD'): # Custom check implemented in conf.py to skip this if we're inside Sphinx
                    try: # First try interactive
                        assert jupyter not in ['default', 'retina'] # Hack to intentionally go to the other part of the loop
                        from IPython import get_ipython
                        magic = get_ipython().magic
                        magic('%matplotlib widget')
                    except: # Then try retina
                        assert jupyter != 'default'
                        import matplotlib_inline
                        matplotlib_inline.backend_inline.set_matplotlib_formats('retina')
            except:
                pass

        # Handle interactivity
        if 'interactive' in kwargs.keys():
            interactive = kwargs['interactive']
            if interactive in [None, 'default']:
                interactive = self.orig_options['interactive']
            if interactive:
                kwargs['show'] = True
                kwargs['close'] = False
                kwargs['backend'] = self.orig_options['backend']
            else:
                kwargs['show'] = False
                kwargs['backend'] = 'agg'

        # Reset options
        for key,value in kwargs.items():

            # Handle deprecations
            rename = {'font_size': 'fontsize', 'font_family':'font'}
            if key in rename.keys():
                from . import misc as hpm # Here to avoid circular import
                oldkey = key
                key = rename[oldkey]
                warnmsg = f'Key "{oldkey}" is deprecated, please use "{key}" instead'
                hpm.warn(warnmsg, FutureWarning)

            if key not in self:
                keylist = self.orig_options.keys()
                keys = '\n'.join(keylist)
                errormsg = f'Option "{key}" not recognized; options are "defaults" or:\n{keys}\n\nSee help(hp.options.set) for more information.'
                raise sc.KeyNotFoundError(errormsg)
            else:
                if value in [None, 'default']:
                    value = self.orig_options[key]
                self[key] = value
                if key in 'backend':
                    pl.switch_backend(value)

        return


    def context(self, **kwargs):
        '''
        Alias to set() for non-plotting options, for use in a "with" block.

        Note: for plotting options, use ``hp.options.with_style()``, which is linked
        to Matplotlib's context manager. If you set plotting options with this,
        they won't have any effect.

        **Examples**::

            # Silence all output
            with hp.options.context(verbose=0):
                hp.Sim().run()

            # Convert warnings to errors
            with hp.options.context(warnings='error'):
                hp.Sim(location='not a location').initialize()

            # Use with_style(), not context(), for plotting options
            with hp.options.with_style(dpi=50):
                hp.Sim().run().plot()

        '''

        # Store current settings
        on_entry = {k:self[k] for k in kwargs.keys()}
        self.setattribute('on_entry', on_entry)

        # Make changes
        self.set(**kwargs)
        return self


    def get_default(self, key):
        ''' Helper function to get the original default options '''
        return self.orig_options[key]


    def changed(self, key):
        ''' Check if current setting has been changed from default '''
        if key in self.orig_options:
            return self[key] != self.orig_options[key]
        else:
            return None


    def help(self, detailed=False, output=False):
        '''
        Print information about options.

        Args:
            detailed (bool): whether to print out full help
            output (bool): whether to return a list of the options

        **Example**::

            hp.options.help(detailed=True)
        '''

        # If not detailed, just print the docstring for hp.options
        if not detailed:
            print(self.__doc__)
            return

        n = 15 # Size of indent
        optdict = sc.objdict()
        for key in self.orig_options.keys():
            entry = sc.objdict()
            entry.key = key
            entry.current = sc.indent(n=n, width=None, text=sc.pp(self[key], output=True)).rstrip()
            entry.default = sc.indent(n=n, width=None, text=sc.pp(self.orig_options[key], output=True)).rstrip()
            if not key.startswith('rc'):
                entry.variable = f'HPVSIM_{key.upper()}' # NB, hard-coded above!
            else:
                entry.variable = 'No environment variable'
            entry.desc = sc.indent(n=n, text=self.optdesc[key])
            optdict[key] = entry

        # Convert to a dataframe for nice printing
        print('hpvsim global options ("Environment" = name of corresponding environment variable):')
        for k, key, entry in optdict.enumitems():
            sc.heading(f'{k}. {key}', spaces=0, spacesafter=0)
            changestr = '' if entry.current == entry.default else ' (modified)'
            print(f'          Key: {key}')
            print(f'      Current: {entry.current}{changestr}')
            print(f'      Default: {entry.default}')
            print(f'  Environment: {entry.variable}')
            print(f'  Description: {entry.desc}')

        sc.heading('Methods:', spacesafter=0)
        print('''
    hp.options(key=value) -- set key to value
    hp.options[key] -- get or set key
    hp.options.set() -- set option(s)
    hp.options.get_default() -- get default setting(s)
    hp.options.load() -- load settings from file
    hp.options.save() -- save settings to file
    hp.options.to_dict() -- convert to dictionary
    hp.options.style() -- create style context for plotting
''')

        if output:
            return optdict
        else:
            return


    def load(self, filename, verbose=True, **kwargs):
        '''
        Load current settings from a JSON file.

        Args:
            filename (str): file to load
            kwargs (dict): passed to ``sc.loadjson()``
        '''
        json = sc.loadjson(filename=filename, **kwargs)
        current = self.to_dict()
        new = {k:v for k,v in json.items() if v != current[k]} # Don't reset keys that haven't changed
        self.set(**new)
        if verbose: print(f'Settings loaded from {filename}')
        return


    def save(self, filename, verbose=True, **kwargs):
        '''
        Save current settings as a JSON file.

        Args:
            filename (str): file to save to
            kwargs (dict): passed to ``sc.savejson()``
        '''
        json = self.to_dict()
        output = sc.savejson(filename=filename, obj=json, **kwargs)
        if verbose: print(f'Settings saved to {filename}')
        return output


    def _handle_style(self, style=None, reset=False, copy=True):
        ''' Helper function to handle logic for different styles '''
        rc = self.rc # By default, use current
        if isinstance(style, dict): # If an rc-like object is supplied directly
            rc = sc.dcp(style)
        elif style is not None: # Usual use case
            stylestr = str(style).lower()
            if stylestr in ['default', 'hpvsim', 'house']:
                rc = sc.dcp(rc_hpvsim)
            elif stylestr in ['simple', 'chpvsim_simple', 'plain', 'clean']:
                rc = sc.dcp(rc_simple)
            elif style in pl.style.library:
                rc = sc.dcp(pl.style.library[style])
            else:
                errormsg = f'Style "{style}"; not found; options are "hpvsim" (default), "simple", plus:\n{sc.newlinejoin(pl.style.available)}'
                raise ValueError(errormsg)
        if reset:
            self.rc = rc
        if copy:
            rc = sc.dcp(rc)
        return rc


    def with_style(self, style_args=None, use=False, **kwargs):
        '''
        Combine all Matplotlib style information, and either apply it directly
        or create a style context.

        To set globally, use ``hp.options.use_style()``. Otherwise, use ``hp.options.with_style()``
        as part of a ``with`` block to set the style just for that block (using
        this function outsde of a with block and with ``use=False`` has no effect, so
        don't do that!). To set non-style options (e.g. warnings, verbosity) as
        a context, see ``hp.options.context()``.

        Args:
            style_args (dict): a dictionary of style arguments
            use (bool): whether to set as the global style; else, treat as context for use with "with" (default)
            kwargs (dict): additional style arguments

        Valid style arguments are:

            - ``dpi``:       the figure DPI
            - ``font``:      font (typeface)
            - ``fontsize``:  font size
            - ``grid``:      whether or not to plot gridlines
            - ``facecolor``: color of the axes behind the plot
            - any of the entries in ``pl.rParams``

        **Examples**::

            with hp.options.with_style(dpi=300): # Use default options, but higher DPI
                pl.plot([1,3,6])
        '''
        # Handle inputs
        rc = sc.dcp(self.rc) # Make a local copy of the currently used settings
        kwargs = sc.mergedicts(style_args, kwargs)

        # Handle style, overwiting existing
        style = kwargs.pop('style', None)
        rc = self._handle_style(style, reset=False)

        def pop_keywords(sourcekeys, rckey):
            ''' Helper function to handle input arguments '''
            sourcekeys = sc.tolist(sourcekeys)
            key = sourcekeys[0] # Main key
            value = None
            changed = self.changed(key)
            if changed:
                value = self[key]
            for k in sourcekeys:
                kwvalue = kwargs.pop(k, None)
                if kwvalue is not None:
                    value = kwvalue
            if value is not None:
                rc[rckey] = value
            return

        # Handle special cases
        pop_keywords('dpi', rckey='figure.dpi')
        pop_keywords(['font', 'fontfamily', 'font_family'], rckey='font.family')
        pop_keywords(['fontsize', 'font_size'], rckey='font.size')
        pop_keywords('grid', rckey='axes.grid')
        pop_keywords('facecolor', rckey='axes.facecolor')

        # Handle other keywords
        for key,value in kwargs.items():
            if key not in pl.rcParams:
                errormsg = f'Key "{key}" does not match any value in HPVsim options or pl.rcParams'
                raise sc.KeyNotFoundError(errormsg)
            elif value is not None:
                rc[key] = value

        # Tidy up
        if use:
            return pl.style.use(sc.dcp(rc))
        else:
            return pl.style.context(sc.dcp(rc))


    def use_style(self, **kwargs):
        '''
        Shortcut to set hpvsim's current style as the global default.

        **Example**::

            hp.options.use_style() # Set hpvsim options as default
            pl.figure()
            pl.plot([1,3,7])

            pl.style.use('seaborn-whitegrid') # to something else
            pl.figure()
            pl.plot([3,1,4])
        '''
        return self.with_style(use=True, **kwargs)


def load_fonts(folder=None, rebuild=False, verbose=False, **kwargs):
    '''
    Helper function to load custom fonts for plotting -- (usually) not for the user.

    Note: if fonts don't load, try running ``hp.settings.load_fonts(rebuild=True)``,
    and/or rebooting the system.

    Args:
        folder (str): the folder to add fonts from
        rebuild (bool): whether to rebuild the font cache
        verbose (bool): whether to print out progress/errors
    '''

    if folder is None:
        folder = str(sc.thisdir(__file__, aspath=True) / 'data' / 'assets')
    sc.fonts(add=folder, rebuild=rebuild, verbose=verbose, **kwargs)

    # Try to find the font, and if it succeeds, update the styles
    try:
        name = 'Mulish'
        fm.findfont(name, fallback_to_default=False) # Raise an exception if the font isn't found
        rc_simple['font.family']  = name # Need to set both
        rc_hpvsim['font.family'] = name
        if verbose: print(f'Default hpvsim font reset to "{name}"')
    except Exception as E:
        if verbose: print(f'Could not find font {name}: {str(E)}')

    return


# Create the options on module load, and load the fonts
options = Options()
