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
import os
import traceback
import sys
import subprocess

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
# TODO Spell check

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
    
    raise InitInputError('var', InputRec, 'message {}'.format())
    """
    def __init__(self, var, InputRec, message):
        self.var = var
        self.message = message
        self.InputRec = InputRec
        
class BoundsInconsistentError(InitInputError):
    """
    Exception raised for errors in lat lon bounds.
    Attributes:
        message -- explanation of the error
        Directions -- the directions in the bounds that are inconsistent (string)
        InputRec -- the improper input
    
    """
    def __init__(self, Directions, InputRec, message):
        super().__init__(Directions, InputRec, message)
        self.Directions = Directions

class ProcessingError(Exception):
    #filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    #print(exc_type, fname, exc_tb.tb_lineno)

    #exc_type, exc_obj, exc_tb = sys.exc_info()   
    # exc_type, exc_value, exc_traceback = sys.exc_info()
    #raise ProcessingError(exc_traceback.tb_lineno, CauseException, "message {}".format())
    def __init__(self, Line, CauseException, message):
        self.Line = Line
        self.message = message
        self.CauseException = CauseException

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
    # TODO update doc string above
    # TODO Implement OutputForHistogram (Input is name atribute of interest - lake area etc)
    
    ALLOWED_INPUTS = ['InputFile',
                        'OutputFile',
                        'SimpleBounds',
                        'BoundsFile',
                        'AreaMin',
                        'AreaMax',
                        'LakeName',
                        'LakeNameFile',
                        'CountryName',
                        'CountryNameFile',
                        'SkipIslands',
                        'RunLoud', 
                        'RunSilent', 
                        'OutputForHistogram', 
                        'Overwrite']
    
    # TODO verify on reading file that this matches
    HEADER_ORDER = ['Hylak_id',
                    'Lake_name',
                    'Country',
                    'Continent',
                    'Poly_src',
                    'Lake_type',
                    'Grand_id',
                    'Lake_area',
                    'Shore_len',
                    'Shore_dev',
                    'Vol_total',
                    'Vol_res',
                    'Vol_src',
                    'Depth_avg',
                    'Dis_avg',
                    'Res_time',
                    'Elevation',
                    'Slope_100',
                    'Wshd_area',
                    'Pour_long',
                    'Pour_lat']
                        
    def __init__(self, InputFile,
                    OutputFile,
                    SimpleBounds=None,
                    BoundsFile=None,
                    AreaMin=None,
                    AreaMax=None,
                    LakeName=None,
                    LakeNameFile=None,
                    CountryName=None,
                    CountryNameFile=None,
                    SkipIslands=False,
                    RunLoud=False, 
                    RunSilent=False, 
                    OutputForHistogram=False, 
                    Overwrite=False):
                    
        global SUPPORTED_INPUT_EXTENSIONS
        
        # Check for infile, outfile
        if RunLoud:
            print("Checking if files exist")
        if os.path.exists(InputFile):
            if RunLoud:
                print(InputFile,'  - exists')
        else:
            #raise InitInputError('var', InputRec, ''.format())
            raise InitInputError('InputFile', InputFile, 'ERROR - No input file found - {}'.format(InputFile))
    
        if (os.path.exists(OutputFile)) and (Overwrite is not True):
            raise InitInputError('OutputFile', OutputFile, 'Output file {}  - exists \nUse -o to overwrite '.format(OutputFile))
        
        # Lake area min and max
        if (AreaMax is not None) and (RunLoud):
            print("Lake AreaMax set to ", AreaMax)
        if (AreaMin is not None) and (RunLoud):
            print("Lake AreaMin set to ", AreaMin)
    
        if (AreaMin is not None) and (AreaMax is not None):
            if AreaMax < AreaMin:
                raise InitInputError('AreaMax AreaMin', [AreaMin,AreaMax], "ERROR - AreaMin {} larger than AreaMax {}. If you don't want an output, don't run the program!".format(AreaMin,AreaMax))
    
        if SimpleBounds is not None:
            try:
                DatelineCrossed = self.BoundsDatelineCheck(SimpleBounds, Verbose=RunLoud)
            except BoundsInconsistentError as err:
                print('ERROR bounds inconsisten')
                print(err.message)
                print('Error in {} directions'.format(err.Directions))
                print('Received bounds {}'.format(err.InputRec))
                print('Exiting')
                raise
            
            SimpleBounds.append(DatelineCrossed)
    
        if BoundsFile is not None:
            if os.path.exists(BoundsFile):
                if RunLoud:
                    print(BoundsFile,'  - exists')
            else:
                raise InitInputError('BoundsFile', BoundsFile, 'ERROR - No bounds file found - {}'.format(BoundsFile))
        
        # TODO Validate bounds File using BoundsDatelineCheck
        
        # Save the inputs to self.<input>
        for Input in self.ALLOWED_INPUTS:
            exec('self.{} = {}'.format(Input,Input))
            if RunLoud:
                print('Set self.{} = {}'.format(Input,eval('self.{}'.format(Input))))
        
        # Temp
        self.HeaderElementsOfInterest = [1, 19, 20]
        
    # Functions to check the lake header against parameters
    def ExtractLakeHeader(self, line):
        """
        Takes a lake header line and returns a dictionary of those header elements of interest.
        """
        LineElements = line[4:].split(sep='|')
        print(line)
        print(LineElements)

        LineElementsSubset = [LineElements for i in self.HeaderElementsOfInterest]
        HeaderListSubset = [self.HEADER_ORDER for i in self.HeaderElementsOfInterest]
        
        # Does not work
        #HeaderDict = dict(zip(HeaderListSubset, LineElementsSubset))
        
        #print(HeaderDict)
        #return HeaderDict
        return True
    
    def LakeMatchesBounds(self):
        return True
    
    def ILakeMatchesArea(self):
        return True
    
    def LakeMatchesName(self):
        return True
        
    def LakeMatchesCountry(self):
        return True
        
    
    def LakeMatchesAllText(self):
        return True
        
    def LakeMatchesAllNumbers(self):
        """
        All numerical limits except bounds
        """
        return True
    
    def ReturnTrue(self, *args):
        return True
    
    def ReturnFalse(self, *args):
        return False
    
    # Functions for handeling files
    def CheckExtension(self, ExtString):
        if (os.path.exists(self.InputFile[:-3]+ExtString.lower())) or (os.path.exists(self.InputFile[:-3]+ExtString.upper())):
            if self.RunLoud:
                print(self.InputFile[:-3]+ExtString, " - exists")
        else:
            if self.RunLoud:
                print("HydroSHEDS distributes .shp, .dbf, .prj, and .shx files in the same zip file. \nThey should be kept in the same directory.\nExcepting")
            raise InitInputError('Input files', self.InputFile[:-3]+ExtString, '{} is missing and will be needed by ogr2ogr.'.format(self.InputFile[:-3]+ExtString))
        
    def CheckAndConvertInFile(self):
        """
        Check to see if input file is type GMT and convert if it is not
        """
        # If .shp input, convert using ogr2ogr from GDAL. Exit with error if ogr2ogr is not accessable.
        InputExtension = self.InputFile[-3:]
        if self.RunLoud:
            print("InputFile extension is", InputExtension)

        if (InputExtension == "shp") or (InputExtension == "SHP"):
            if self.RunLoud:
                print("Converting to gmt type file with GDAL ogr2ogr")
        
            #ogr2ogr expects an shx file
            # It also needs dbf and prj files but will silently produce undesired output if not provided
            self.CheckExtension('shp')
            self.CheckExtension('shx')
            self.CheckExtension('dbf')
            self.CheckExtension('prj')
            
            IntermediateFileName = self.InputFile[:-4] + '_TempConv.gmt'
            self.InFileGMTtxt = IntermediateFileName
            if self.RunLoud:
                print("Will create temporary intermediate file\n  {}".format(IntermediateFileName))
    
    
            # Call ogr2ogr GDAL
            if self.RunLoud:
                CommandString = 'ogr2ogr -f "GMT" ' + IntermediateFileName + ' ' + self.InputFile + ' --debug ON'
            elif not self.RunSilent:
                CommandString = 'ogr2ogr -f "GMT" ' + IntermediateFileName + ' ' + self.InputFile 
            else:
                CommandString = 'ogr2ogr -f "GMT" ' + IntermediateFileName + ' ' + self.InputFile + ' --debug OFF >/dev/null 2>&1'
    
            try:
                if self.RunLoud:
                    print("Running: ", CommandString, "\n")
                    
                #ExitStatus = os.system(CommandString)
                #ProcessInfo = subprocess.run(CommandString, check=True) # Run opens a new shell. Does not work if we get gdal from GMT
                #ExitStatus = subprocess.call(CommandString, shell=True)
                ProcessInfo = subprocess.run(CommandString, check=True, shell=True, text=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                ExitStatus = ProcessInfo.returncode
                if self.RunLoud:
                    print('ProcessInfo.stdout')
                    print(ProcessInfo.stdout)
                    print('ProcessInfo.stderr')
                    print(ProcessInfo.stderr)
                    print('ProcessInfo')
                    print(ProcessInfo)

            except subprocess.CalledProcessError as err:
                print(" Error unable to run ",CommandString)
                print("CalledProcessError")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if RunLoud:
                    print(err.output)
                    print(err.stdout)
                    print(err.stderr)
                    print(err)
                # Special case - cannot find ogr2ogr
                if "ogr2ogr: command not found" in err.stderr:
                    print("\n*\n*\n*\n ogr2ogr was not found\n  It may not be installed. \n  If you use GMT to access it,\n  start GMT and run ParseSHEDSLake from the same shell.\n*\n\n\n")
                    raise ProcessingError(exc_traceback.tb_lineno, err, "ERROR ogr2ogr: command not found - try running it alone from the command line to see if you can reach it.")
                
                if self.RunLoud:
                    traceback.print_tb(exc_traceback)
                raise ProcessingError(exc_traceback.tb_lineno, err, "ERROR running {} received CalledProcessError".format(CommandString))
            except FileNotFoundError as err:
                print(" Error unable to run ",CommandString)
                print("FileNotFoundError")
                print(err)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if self.RunLoud:
                    traceback.print_tb(exc_traceback)
                raise ProcessingError(exc_traceback.tb_lineno, err, "ERROR running {} received FileNotFoundError".format(CommandString))

            


            if self.RunLoud:
                print("ogr2ogr exit status: ",ExitStatus)
                print("\n")
            if ExitStatus != 0:
                print("ogr2ogr appears to have failed.\nIt may be that you need to open GMT to access GDAL ogr2ogr. \nExiting")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                raise ProcessingError(exc_traceback.tb_lineno, '', "ERROR non zero exit {} running {}".format(ExitStatus,CommandString))
    
        
        elif (InputExtension == "gmt") or (InputExtension == "GMT"):
            if self.RunLoud:
                print("File type is gmt")
    
            self.InFileGMTtxt = self.InputFile
    
        else:
            print("\nError input file type not supported. \nSupported extensions are: ",SUPPORTED_INPUT_EXTENSIONS)
            raise InitInputError('InputFile', self.InputFile, 'InputFile extension not supported {}. Supported types {}'.format(InputExtension, SUPPORTED_INPUT_EXTENSIONS))
        
        
    # Main Loop Function
    def ParseLAKES(self):
    
        self.CheckAndConvertInFile()
    
        # Open the files
        # Copy the top header
        # loop over each line
            # find headers
            # check for matches and copy
        # Close the file
        
        # Move down the input file line by Line
        InFile = open(self.InFileGMTtxt, 'r')
        OutFile = open(self.OutputFile, 'w')
        
        CountLines = 0
        CountLakes = 0
        CountTotalIslands = 0
        CountIslandsThisLake = 0
        MostIslandsInLake = 0
        SmallestLake = 24709000
        LargestLake = 0
        CountLakesCopied = 0
        CountTotalIslandsCopied = 0
        SmallestLakeCopied = 24709000
        LargestLakeCopied = 0
        
        HeaderFound = False
        LakeHeaderFound = False
        IslandHeaderFound = False
        SkipThisLake = False
        SkipUntilHeader = False
        AboutToCopyFirstLine = False
        SkipIslandsInThisLake = self.SkipIslands
        
        SavedCommentLine = ''
        
        for line in InFile:
            CountLines += 1
            
            # After each segment header > line look for a comment line with @D or @H
            # In the GMT format HydroLAKES file, each lake has a header with the info above. Lake perimeters begin with
            # > (without the #)
            # @D <Info on lake>
            # @P
            # and island perimeters begin with 
            # > (without the #)
            # @H
            if HeaderFound:
                HeaderFound = False
                # The last line was a header so is this an island or a new lake
                if line.startswith('# @D'):
                    # Its a new Lake
                    LakeHeaderFound = True
                    CountLakes += 1
                    if CountIslandsThisLake > MostIslandsInLake:
                        MostIslandsInLake = CountIslandsThisLake
                        CountIslandsThisLake = 0
                    
                    dict = self.ExtractLakeHeader(line)
                    
                    # temp
                    #OutFile.write(">\n")
                    #OutFile.write(line)
                elif line.startswith('# @H'):
                    # Its an island
                    IslandHeaderFound = True
                    CountTotalIslands += 1
                    CountIslandsThisLake += 1
                    
                    # temp
                    OutFile.write(">\n")
                    OutFile.write(line)
                else:
                    print("Warning odd header after > {}. Continuing.".format(line))

        
#                 try:
#                     UpstreamCells = self.ParseUpstreamCells(line)
#                 except UpstreamCountError as err:
#                     if not self.RunSilent:
#                         print("Error unable to parse comment on line {}. Continuing.".format(CountLines))
#                         print(err)
#                     UpstreamCells = 0
#                 else:
#                     #Keep track of largest and smallest upstream - if no exception
#                     if UpstreamCells > LargestUpstreamCells:
#                         LargestUpstreamCells = UpstreamCells
#                     if UpstreamCells < SmallestUpstreamCells:
#                         SmallestUpstreamCells = UpstreamCells
#             
#                 # If TL or TH are set we only want to 
#                 # If the count is between thresholds 
#                 #  Output a new segment header > with proper -W pen options
#                 # If the count is out of threshold, skip this segment and look for the next One
#                 if self.UpstreamCellsWithinLimits(UpstreamCells):
#                     SkipThisSegment = False
#                     AboutToCopyFirstSegmentLine = True
#             
#                 else:
#                     SkipThisSegment = True
            
            # Skip line if only white space (\n etc)
            if line.isspace():
                pass
    
            # Skip segment headers and set flag to add them back.
            elif line[0] == ">":
                HeaderFound = True
        
            # Skip segments including comment lines if previously identified for skipping
            elif SkipUntilHeader:
                pass
        
            # Reproduce each comment line as is
            elif line[0] == "#":
#                 if AboutToCopyFirstLine:
#                     SavedCommentLine = line
#                 else:
#                     # This will simply write out the header at the top of the document.
#                     # And it will copy the # @P lake paremeter marker if the lake is not being skipped.
#                     OutFile.write(line)
                # For now, no need for anything fancy here - just copy # @P and the stuff at the top
                OutFile.write(line)
                
            
    
            # check for in bounds on first line if enabled
#             elif line[1].isdigit() and AboutToCopyFirstSegmentLine:
#                 # If any bounding is set
#                 if self.CopyWithinBounds is not False:
#                     AboutToCopyFirstSegmentLine = False
#         
#                     # Order in gmt files is Lon Lat 142.245833333334 -10.133333333333
#                     Lon,Lat = line.split()
#                     Lat = float(Lat)
#                     Lon = float(Lon)
#         
#                     if self.CheckBounds(Lat,Lon):
#                         CountSegmentsCopied += 1
#             
#                         if self.SegmentHeaderIsSimple:
#                             OutFile.write(">\n")
#                         else:
#                             OutFile.write(self.CreateSegmentHeader(UpstreamCells))
#                 
#                         OutFile.write(SavedCommentLine)
#                         OutFile.write(line)
#                     else:
#                         SkipThisSegment = True
                
                # else no bounding is set so write the header and first line
#                 else:
#                     CountSegmentsCopied += 1
#                     AboutToCopyFirstSegmentLine = False
#             
#                     if self.SegmentHeaderIsSimple:
#                         OutFile.write(">\n")
#                     else:
#                         OutFile.write(self.CreateSegmentHeader(UpstreamCells))
#             
#                     OutFile.write(SavedCommentLine)
#                     OutFile.write(line)
                    

    
            #  Reproduce each data line as is. The first character might be a minus. 
            # Other chars might be . 
            # 9.500 95.00 950.0 -9.500 -95.00 -950.0
            elif line[0].isdigit() or line[1].isdigit():
                OutFile.write(line)
    
            else:
                if not self.RunSilent:
                    print("Warning unexpected line start. Skipping line {}".format(CountLines))
                    print(line)

            
            
        # Close input and output files at EOF
        InFile.close()
        OutFile.close()
        
        self.FileStats = {'CountLakes':CountLakes,
                            'CountTotalIslands':CountTotalIslands,
                            'MostIslandsInLake':MostIslandsInLake,
                            'CountLines':CountLines,
                            'MostIslandsInLake':MostIslandsInLake,
                            'SmallestLake':SmallestLake,
                            'LargestLake':LargestLake,
                            'CountLakesCopied':CountLakesCopied,
                            'CountTotalIslandsCopied':CountTotalIslandsCopied,
                            'SmallestLakeCopied':SmallestLakeCopied,
                            'LargestLakeCopied':LargestLakeCopied}

    
    @classmethod
    def BoundsDatelineCheck(self, Bounds, Verbose=False):
        """
        Checks for self consistency in lat lon bounds. W E S N order is expected. 
        Returns True if the bounds include the dateline. False if not. Raises 
        BoundsInconsistentError if there is an error.
    
        Bounds should be a list of len 4 [W E S N]
        Verbose is bool
        """

        # Check Lat
        if (Bounds[2] < Bounds[3]):
            if Verbose:
                print('Southern limit is south of northern')
        else:
            #raise BoundsInconsistentError(Directions, Bounds, message)
            raise BoundsInconsistentError('SN', Bounds, 'ERROR southern limit {} is not south of northern {}'.format(Bounds[2], Bounds[3]))
    
        
        # Southern limit should be somewhere on earth
        if (Bounds[2] >= -90.0) and (Bounds[2] <= 90.0):
            if Verbose:
                print('Southern limit is good')
        else:
            raise BoundsInconsistentError('S', Bounds, 'ERROR with southern limit {}'.format(Bounds[2]))
    
        # Northern limit should be somewhere on earth and north of Southern limit
        if (Bounds[3] >= -90.0) and (Bounds[3] <= 90.0):
            if Verbose:
                print('Northern limit is good')
        else:
            raise BoundsInconsistentError('N', Bounds, 'ERROR with northern limit {}'.format(Bounds[3]))
        
        # Check Lon
        if (Bounds[0] != Bounds[1]):
            if Verbose:
                print('Western limit different from eastern')
        else:
            raise BoundsInconsistentError('WE', Bounds, 'ERROR western limit {} is the same as eastern {}'.format(Bounds[0], Bounds[1]))
    
        # West limit should be somewhere on earth and west of eastern limit (but the sphere is continuous so...)
        if (Bounds[0] >= -180.0) and (Bounds[0] <= 180.0) and (Bounds[0] != Bounds[1]):
            if Verbose:
                print('Western limit is good')
        else:
            raise BoundsInconsistentError('W', Bounds, 'ERROR with Western limit {}'.format(Bounds[0]))
    
        # East limit should be somewhere on earth and east of western limit (but the sphere is continuous so...)
        if (Bounds[1] >= -180.0) and (Bounds[1] <= 180.0) and (Bounds[0] != Bounds[1]):
            if Verbose:
                print('Eastern limit is good')
        else:
            raise BoundsInconsistentError('E', Bounds, 'ERROR with eastern limit {}'.format(Bounds[1]))

        if Bounds[0] <  Bounds[1]:
            if Verbose:
                print('Does not cross dateline')
            BoundsIncDateline = False
        else:
            if Verbose:
                print('Bounds include the dateline. Now things are complicated')
            BoundsIncDateline = True
    
        if Verbose:
            print("Limits are W: {} E: {} S: {} N: {} Dateline crossed: {}".format(Bounds[0],Bounds[1],Bounds[2],Bounds[3],BoundsIncDateline))
    
        return BoundsIncDateline
        # End BoundsDatelineCheck()
    


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
                        
    parser.add_argument("-oi", "-si", "-OI", "-SI", "--SkipIslands", action="store_true",
                        help="Do not output island polygons. GMT will plot lakes as though there are no islands.")
                        
    BoundsGroup = parser.add_mutually_exclusive_group(required=False)
    BoundsGroup.add_argument("-B", "-b", "--Bounds", action="store", nargs=4, type=float, metavar=('W', 'E', 'S', 'N'),
                        help="Set limits on which lakes to output based on latitude and longitude.\nOnly the pour point will be checked. Lake parts may leave the boundry. \nUse decimal notation and - for south and west.")
    BoundsGroup.add_argument("-BF", "-bf", "--BoundsFile", action="store", nargs=1,
                            help="Only output lakes within one of the bounds in BoundsFile. The file should have one set of bounds per line in order: W E S N. Use decimal degrees and - for south and west.")
    
    parser.add_argument("-AL", "-al", "--AreaMin", action="store", nargs=1, type=float, metavar='km^2',
                        help="Minimum lake area in square kilometers. Only lakes >= AreaMin will be included.")
    parser.add_argument("-AU", "-au", "--AreaMax", action="store", nargs=1, type=float, metavar='km^2',
                        help="Maximum lake area in square kilometers. Only lakes <= AreaMax will be included.")
    
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
    
    if args.verbose is True:
        RUN_LOUD = True
    else:
        RUN_LOUD = False

    # verbose supersedes silent
    if RUN_LOUD:
        print("RUN_LOUD true")
        RUN_SILENT = False
    elif args.silent is True:
        RUN_SILENT = True
    else:
        RUN_SILENT = False
    
    if not RUN_SILENT:
        print("\nParse SHEDS Lake Starting\n\n")
        print("The HydroLAKES license requires atribution. \nSee tecnincal documentation at https://www.hydrosheds.org/page/hydrolakes \n\n")

    if (args.Overwrite is True):
        OVERWRITE_FILES = True
        if RUN_LOUD:
            print("Warning will overwrite OutputFile if it exists")
    else:
        OVERWRITE_FILES = False
        
    if (args.SkipIslands is True):
        SkipIslands = True
        if RUN_LOUD:
            print("Skipping all islands! \n\n    Why would you do that?!?")
    else:
        SkipIslands = False
        
    # Loop over input parameters and prepare to send them to the LakesParser class
    # Special cases: These names do not match between the argparser and LakesParser init 
    #print(LakesParser.ALLOWED_INPUTS)
    InputsList = LakesParser.ALLOWED_INPUTS.copy()
    InputsList.remove('RunLoud')
    RunLoud = RUN_LOUD
    InputsList.remove('RunSilent')
    RunSilent = RUN_SILENT
    InputsList.remove('Overwrite')
    Overwrite = OVERWRITE_FILES
    InputsList.remove('SkipIslands')
    #SkipIslands = SkipIslands above
    
    # TODO implement OutputForHistogram
    InputsList.remove('OutputForHistogram')
    
    # Bounds is a list so [0] would cause issues
    InputsList.remove('SimpleBounds')
    SimpleBounds = args.Bounds
    
    for Input in InputsList:
        # eval cannot handle setting a value to a var - use exec
        # None[0] spits an error so...
        if eval('args.{}'.format(Input)) is not None:
            exec('{} = args.{}[0]'.format(Input,Input))
            if RUN_LOUD:
                print('Received {} {}'.format(Input,eval(Input)))

        else:
            exec('{} = args.{}'.format(Input,Input))
           
         
    #Instantiate
    try:
        ParserObj = LakesParser(InputFile=InputFile,
                                OutputFile=OutputFile,
                                SimpleBounds=SimpleBounds,
                                BoundsFile=BoundsFile,
                                AreaMin=AreaMin,
                                AreaMax=AreaMax,
                                LakeName=LakeName,
                                LakeNameFile=LakeNameFile,
                                CountryName=CountryName,
                                CountryNameFile=CountryNameFile,
                                SkipIslands=SkipIslands,
                                RunLoud=RunLoud, 
                                RunSilent=RunSilent, 
                                OutputForHistogram=False, 
                                Overwrite=Overwrite)
    except InitInputError as err:
        print("ERROR - FAIL")
        print(err.message)
        print('Exiting with code 15')
        exit(15)
    
    try:
        ParserObj.ParseLAKES()
    except InitInputError as err:
        print("ERROR - FAIL")
        print(err.message)
        print('Exiting with code 15')
        exit(15)
    except ProcessingError as err:
        print("ERROR - FAIL")
        print(err.Line)
        print(err.CauseException)
        print(err.message)
        print('Exiting with code 16')
        exit(16)
        
    if not RUN_SILENT:
        print(ParserObj.FileStats)
