"""
Parse SHEDS Lake is a Python program to parse HydroSHEDS lake data, HydroLAKES, for GMT.

Usage: python3 ParseSHEDSLake.py InputFile.gmt OutputFile.gmt

Input: HydroSHEDS lakes (HydroLAKES) file converted to GMT text format 
        (exempli gratia HydroLAKES_polys_GMT.gmt)
    OR HydroLAKES Lake polygons file in original ESRI Shapefile format 
       IF ogr2ogr from GDAL is accessable via os.system('ogr2ogr')
        (exempli gratia HydroLAKES_polys_v10.shp)
        
Output: GMT polygon file in .gmt format 
        with segment headers separating each lake

The HydroSHEDS HydroLAKES data has perimeter polygons for lakes 10 ha and larger. Most
of the world is covered and in particular 56 ̊S to 60 ̊N plus certain more northern 
regions. This data is in the form of closed polygons of the lake permiter. Headers for
each lake provide further information. Completness is reportedly somewhere around 35 ha 
and larger.



HydroSHEDS data is available at https://www.hydrosheds.org/
Users should review carefully the license in the technical documentation at 
https://www.hydrosheds.org/page/hydrolakes 
Note that the license requires an attribution.

The Author is not affiliated with HydroSHEDS or HydroLAKES.

Run with -h for help.

Object: This may be run as an object. Import ParseSHEDSLake and instantiate the class
LakesParser. Then run ParseLakes(). For example

import ParseSHEDSLake

TheParser = ParseSHEDSLake.LakesParser(InFile,OutFile, *optional options)
TheParser.ParseLakes()

See ParseSHEDSLake.LakesParser.__doc__ for details.

Author: Joseph Wellhouse
Last Update: 2020-07-14
"""

#import argparse # Used and imported in __main__ only

# Meta data in HydroLAKES 
# # @NHylak_id|Lake_name|Country|Continent|Poly_src|Lake_type|Grand_id|Lake_area|Shore_len|Shore_dev|Vol_total|Vol_res|
#Vol_src|Depth_avg|Dis_avg|Res_time
#|Elevation|Slope_100|Wshd_area|Pour_long|Pour_lat
# @Tinteger|string|string|string|string|integer|integer|double|double|double|double|double|integer|double|double|double|integer|double|double|double|double

# In the GMT format HydroLAKES file, each lake has a header with the info above. Lake perimeters begin with
# > (without the #)
# @D <Info on lake>
# @P
# and island perimeters begin with 
# > (without the #)
# @H

# Parse Actions
# select by region of pour point lat lon (Including using a grid file)
# Select by ID,name, country etc
# upper lower limits on lake area, shore len, vol etc
# Remove Islands
# Get statistics

# Efficiency
# check for > then @D
#  Be efficient about selections

# check to see if skipping lake without doing much with the line

# TODO ignore capitalization in names

__version__ = "0.0.1"
__author__ = "Joseph Wellhouse"

SUPPORTED_INPUT_EXTENSIONS = ["shp","gmt"]

class InitInputError(Exception):
    """
    Exception raised for errors in initial setup of class LakesParser.
    Attributes:
        message -- explanation of the error
        var -- the variable which caused the error
        InputRec -- the improper input
    
    """
    def __init__(self, var, InputRec, message):
        self.var = var
        self.message = message
        self.InputRec = InputRec


class LakesParser:
    """
    Class wrapper for parsing HydroLAKES polygon data for GMT. 
    
    Users should review carefully the license at https://www.hydrosheds.org/page/hydrolakes 
    Note that the license requires an attribution. Details on the license page.

    The Author is not affiliated with HydroSHEDS or HydroLAKES.
    
    See __doc__ for ParseSHEDSLake.py for details.
    
    Required inputs: InputFile, OutputFile
    
    Optional inputs:    
                        SimpleBounds=None,
                        BoundsFile=None,
                        RunLoud=False, 
                        RunSilent=False, 
                        OutputForHistogram=False, 
                        Overwrite=False
                        
    Run <LakesParser object name>.ParseLAKES() after instantiating.
    
    Access <LakesParser object name>.FileStats for a dictionary of statistics 
    after running ParseLAKES().
    """
    def __init__(self, InputFile,
                    OutputFile,
                    SimpleBounds=None,
                    BoundsFile=None,
                    LakeName=None,
                    LakeNameFile=None,
                    CountryName=None,
                    CountryNameFile=None,
                    RunLoud=False, 
                    RunSilent=False, 
                    OutputForHistogram=False, 
                    Overwrite=False):
                    
        global SUPPORTED_INPUT_EXTENSIONS
    
    def ParseLAKES(self):
        pass



if __name__ == "__main__":
    print("Running Parse SHEDS Lake as __main__")
    
    import argparse
    

    parser = argparse.ArgumentParser(description='Parse HydroSHEDS River Network files for GMT',
                                        epilog='All files except InputFile and OutputFile will be loaded in memory. Keep them small unless you want to fill your RAM.')
    
    parser.add_argument("InputFile", action="store", nargs=1, 
                        help="Name of input file. Either relative or full path. Supports: {}".format(SUPPORTED_INPUT_EXTENSIONS))
    parser.add_argument("OutputFile", action="store", nargs=1, 
                        help="Name of output file. Either relative or full path. Extension will be .gmt")
                        
    parser.add_argument("-d", "--detailedinfo", action="store_true",
                        help="Print detailed script info and exit")
    parser.add_argument('--version', action='version',
                        version="%(prog)s {}".format(__version__))
                    
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Increase output verbosity")
    parser.add_argument("-s", "--silent", action="store_true",
                        help="Run without terminal output except for program failure. Overridden by verbose")
                    
    parser.add_argument("-o", "--Overwrite", action="store_true",
                        help="Overwrite exisiting output. Default is to exit if OutputFile exists.")
                        
    BoundsGroup = parser.add_mutually_exclusive_group(required=False)
    BoundsGroup.add_argument("-B", "-b", "--Bounds", action="store", nargs=4, type=float, metavar=('W', 'E', 'S', 'N'),
                        help="Set limits on which lakes to output based on location.\nOnly the pour point will be checked. Lake parts may leave the boundry. \nUse decimal notation and - for south and west.")
    BoundsGroup.add_argument("-BF", "-bf", "--BoundsFile", action="store", nargs=1,
                            help="Only output lakes within one of the bounds in BoundsFile. The file should have one set of bounds per line in order: W E S N. Use decimal degrees and - for south and west.")
    
    NameGroup = parser.add_mutually_exclusive_group(required=False)
    NameGroup.add_argument("-LN", "-ln", "--LakeName", action="store", nargs=1,
                            help="Only output lakes named LakeName. Use -LN ! for only lakes with empty name field.")
    NameGroup.add_argument("-LNF", "-lnf", "--LakeNameFile", action="store", nargs=1,
                            help="Only output lakes listed in LakeNameFile. The file should have one lake name per line.")
                            
    CountryGroup = parser.add_mutually_exclusive_group(required=False)
    CountryGroup.add_argument("-CN", "-cn", "--CountryName", action="store", nargs=1, metavar="Country",
                            help="Only output lakes in country CountryName. Use -CN ! for only lakes with empty country field.")
    CountryGroup.add_argument("-CNF", "-cnf", "--CountryNameFile", action="store", nargs=1,
                            help="Only output for countries listed in CountryNameFile. The file should have one country name per line")
    
    args = parser.parse_args()
    
    #print(args.LakeName)
    
    # Bring in flags and run some initial tests
    if args.detailedinfo:
        print(__doc__)
        exit(0)
        
    
    # Instantiate and run
    try:
        ParserObj = LakesParser()
    except InitInputError as err:
        print("ERROR - FAIL")
        print(err.message)
        exit(15)
