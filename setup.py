try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

try:
    from Cython.Distutils import build_ext

    ext_modules=[
        Extension("pgpal._yj1",
                sources=["yj1backend/_yj1.pyx"],
        )
    ]
    ext_kwargs = dict(
        cmdclass={'build_ext': build_ext},
        ext_modules = ext_modules
    )
except ImportError:
    ext_kwargs = {}

setup(
    name="PyGame-Pal",
    description="A pygame-based open-source re-implemention of the classic Chinese RPG game 'Chinese Paladin'",
    license="GPLv3",
    install_requires=[
        'cython',
        'pygame',
        'attrs',
        'configobj',
        'charset-normalizer',
        'pyaudio',
        'wrapt',
        'mido',
        'pyperclip',
    ],
    extras_require={
        'rix': ['pyopl'],
        'video': ['pyav >= 0.4.0'],
        'console': ['ptpython'],
    },
    packages=['pgpal',
              'pgpal.configpage'],
    package_dir={'pgpal': 'pgpal',
                 'pgpal.configpage': 'pgpal/configpage'},
    scripts=['pygame-pal.py', 'pgpal-config.py'],
    **ext_kwargs
)
