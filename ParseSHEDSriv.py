"""
Parse SHEDS riv is a Python program to parse HydroSHEDS river network (riv) data for GMT.

Usage: ParseSHEDSriv.py InputFile.gmt OutputFile.gmt

Input: HydroSHEDS River Network file converted to GMT text format 
        (exempli gratia au_riv_15s_Converted.gmt)
    OR HydroSHEDS River Network file in original ESRI Shapefile format 
       IF ogr2ogr from GDAL is accessable via os.system('ogr2ogr')
        (exempli gratia au_riv_15s.shp)
        
Output: GMT vector file in .gmt format 
        with segment headers specifying a -W pen for gmt plot

The HydroSHEDS River Network data (HydroSHEDS RIV) has a considerable amount of location 
data for waterways and drainages worldwide. This data is in the form of vectors tracing
the paths of the waterways. 

Unfortunately, while this data is highly complete, it does not distinguish well between
different types of waterways. Named rivers are not identified or separated from interment
streams. A crude measure of how much water if fed into a given segment is provided in the
form a count of the number of upstream cells. When the .shp ESRI Shapefile is converted
with GDAL ogr2ogr, this count is placed in a comment line below the segment header. The
comment also includes the unique segment identifier. 

This script uses the upstream cell count to apply different modifications to each segment
header. Segments with counts larger or smaller than specified high or low thresholds may
be omitted. -Wpen options may be added to the segment header. Thise will be used by gmt
plot, see https://docs.generic-mapping-tools.org/latest/plot.html#segment-header-parsing 

HydroSHEDS data is available at https://www.hydrosheds.org/
Users should review carefully the license at https://www.hydrosheds.org/page/license
Note that the license requires an attribution. Details on the license page.

The Author is not affiliated with HydroSHEDS.

Run with -h for help and -hp for further help on pens.

Author: Joseph Wellhouse
Last Update: 2020-07-14
"""

# TODO bounds based on grid
# TODO blocking file to remove certain segments
# TODO Replace exits with raise exceptions

__version__ = "0.0.3"
__author__ = "Joseph Wellhouse"

# Program Flow
# Receive calling Parameters
# Check for infile, outfile, properly formated options
# If .shp input, convert using ogr2ogr from GDAL. Exit with error if ogr2ogr is not accessable.

# If specified parse the file for the largest and smallest upstream count

# Move down the input file line by Line
# Reproduce each comment line as is
# After each segment header > look for a comment line of the format 
# @A###|###
# The integer after the | is a count of upstream cells
# If the count is between thresholds 
#  Output a new segment header > with proper -W pen options
#  Reproduce each data line as is
# If the count is out of threshold, skip this segment and look for the next One

# Close input and output files at EOF

# Report count of segments in input and segments in output
# Report range of upstream cells in input and output

SUPPORTED_INPUT_EXTENSIONS = ["shp","gmt"]
PEN_HELP_TEXT = "Pen Help goes here"

# import argparse if called as __main__ only
import os
import traceback
import sys


    
# Exceptions
class UpstreamCountError(Exception):
    """
    Exception raised for errors in parsing the comment line after a segment header.

    Attributes:
        line -- the input line
        message -- explanation of the error
    """
    def __init__(self, line, message):
        self.line = line
        self.message = message
        
class InitInputError(Exception):
    """
    Exception raised for errors in initial setup of class SHEDSrivParser.
    Attributes:
        message -- explanation of the error
        var -- the variable which caused the error
        InputRec -- the improper input
    
    """
    def __init__(self, var, InputRec, message):
        self.var = var
        self.message = message
        self.InputRec = InputRec

class SHEDSrivParser:
    """
    Class wrapper for parsing HydroSHEDS river network (riv) data for GMT. 
    Users should review carefully the license at https://www.hydrosheds.org/page/license
    Note that the license requires an attribution. Details on the license page.

    The Author is not affiliated with HydroSHEDS.
    
    See __doc__ for ParseSHEDSriv.py for details.
    
    """

    def __init__(self, InputFile,
                    OutputFile,
                    ThresholdHigh=None, 
                    ThresholdLow=None, 
                    PenColour=None, 
                    PenWidth=None, 
                    SimpleBounds=None,
                    BoundsFile=None,
                    RunLoud=False, 
                    RunSilent=False, 
                    OutputForHistogram=False, 
                    Overwrite=False):
                    
        global SUPPORTED_INPUT_EXTENSIONS
        #print("SUPPORTED_INPUT_EXTENSIONS")
        #print(SUPPORTED_INPUT_EXTENSIONS)

        BoolInputs = {"RunLoud":RunLoud, "RunSilent":RunSilent, "OutputForHistogram":OutputForHistogram, "Overwrite":Overwrite }
        for key, value in BoolInputs.items():
            if isinstance(value, bool):
                pass
            else:
                raise InitInputError(key,value,'ERROR SHEDSrivParser class init - {} should be bool, received {} of type {}'.format(key, value, type(value)))
       
        self.RunLoud = RunLoud
        self.RunSilent = RunSilent
       
       
        if os.path.exists(InputFile):
            if RunLoud:
                print(InputFile,'  - exists')
        else:
            raise InitInputError("InputFile", InputFile, 'ERROR SHEDSrivParser class init - no path to InputFile:  {} '.format(InputFile))
        
        InputExtension = InputFile[-3:]

        if InputExtension in SUPPORTED_INPUT_EXTENSIONS:
            pass
        else:
            raise InitInputError("InputFile", InputFile, 'ERROR SHEDSrivParser class init - InputFile type not supported:  {} supported types {} '.format(InputFile, SUPPORTED_INPUT_EXTENSIONS))
       
        if os.path.exists(OutputFile) and (Overwrite is False):
            raise InitInputError("OutputFile", OutputFile, 'ERROR SHEDSrivParser class init - OutputFile exists and overwrite is False:  {} '.format(OutputFile))
            
        if BoundsFile is not None:
            if os.path.exists(BoundsFile):
                if RunLoud:
                    print(BoundsFile,'  - exists')
            else:
                raise InitInputError("BoundsFile", BoundsFile, 'ERROR SHEDSrivParser class init - no path to BoundsFile:  {} '.format(BoundsFile))
       
        if isinstance(ThresholdHigh, int) and (ThresholdHigh is not None):
            pass
        else:
            raise InitInputError("ThresholdHigh",ThresholdHigh,'ERROR SHEDSrivParser class init - ThresholdHigh should be int, received {} of type {}'.format(ThresholdHigh, type(ThresholdHigh)))

        if isinstance(ThresholdLow, int) and (ThresholdLow is not None):
            pass
        else:
            raise InitInputError("ThresholdLow",ThresholdLow,'ERROR SHEDSrivParser class init - ThresholdLow should be int, received {} of type {}'.format(ThresholdLow, type(ThresholdLow)))

        if isinstance(SimpleBounds, list) and (SimpleBounds is not None):
            if len(SimpleBounds) == 4:
                if self.ValidateSimpleBounds(SimpleBounds):
                
                    if SimpleBounds[0] <  SimpleBounds[1]:
                        if RUN_LOUD:
                            print('Does not cross dateline')
                        BoundsIncDateline = False
                    else:
                        if RUN_LOUD:
                            print('Bounds include the dateline. Now things are complicated')
                        BoundsIncDateline = True
                        
                    ExpandedSimpleBounds = SimpleBounds.copy()
                    ExpandedSimpleBounds.append(BoundsIncDateline)
                    
                else:
                    raise InitInputError("SimpleBounds",SimpleBounds,'ERROR SHEDSrivParser class init - SimpleBounds not valid should be WESN, received {}'.format(SimpleBounds))
            else:
                raise InitInputError("SimpleBounds",SimpleBounds,'ERROR SHEDSrivParser class init - SimpleBounds should be list of len 4, received {} of type {} and len {}'.format(SimpleBounds, type(SimpleBounds), len(SimpleBounds)))
        else:
            raise InitInputError("SimpleBounds",SimpleBounds,'ERROR SHEDSrivParser class init - SimpleBounds should be list of len 4, received {} of type {}'.format(SimpleBounds, type(SimpleBounds)))



        #self.RunLoud = RunLoud         # Already done
        #self.RunSilent = RunSilent     # Already done
        self.OutputForHistogram = OutputForHistogram
        self.Overwrite = Overwrite
        self.ThresholdHigh = ThresholdHigh
        self.ThresholdLow = ThresholdLow
        self.PenColour = PenColour
        self.PenWidth = PenWidth
        self.SimpleBounds = ExpandedSimpleBounds
        self.BoundsFile = BoundsFile
        self.InputFile = InputFile
        self.OutputFile = OutputFile
        
        if (self.SimpleBounds is not None) or (self.BoundsFile is not None):
            self.CopyWithinBounds = True
        else:
            self.CopyWithinBounds = False
            
        # Thresholds are expected and thus set to low and high values if not set
        if ThresholdHigh is not None:
            self.MaxUpstream = ThresholdHigh
            if not self.RunSilent:
                print("self.MaxUpstream set to ", self.MaxUpstream)
        else:
            self.MaxUpstream = 100000000000   # Intended to be so large it is never an issue
    
        if ThresholdLow is not None:
            self.MinUpstream = ThresholdLow
            if not self.RunSilent:
                print("self.MinUpstream set to ", self.MinUpstream)
        else:
            self.MinUpstream = -1 # All upstream counts are positive so all will be > -1
        
        # If nothing special is set with the pen, the header will be a simple >
        if (PenColour is None) and (PenWidth is None):
            self.SegmentHeaderIsSimple = True
        else:
            self.SegmentHeaderIsSimple = False
        
        # end init
    
    def ValidateSimpleBounds(self, BoundsList):
        # Check Lat
        if (BoundsList[2] < BoundsList[3]):
            if self.RunLoud: 
                print('Southern limit is south of northern')
        else:
            print('ERROR southern limit {} is not south of northern {}'.format(BoundsList[2], BoundsList[3]))
            return False

    
        # Southern limit should be somewhere on earth 
        if (BoundsList[2] >= -90.0) and (BoundsList[2] <= 90.0):
            if self.RunLoud:
                print('Southern limit is good')
        else:
            print('ERROR with southern limit {}'.format(BoundsList[2]))
            return False

        # Northern limit should be somewhere on earth
        if (BoundsList[3] >= -90.0) and (BoundsList[3] <= 90.0):
            if self.RunLoud:
                print('Northern limit is good')
        else:
            print('ERROR with northern limit {}'.format(BoundsList[3]))
            return False
    
        # Check Lon
        if (BoundsList[0] != BoundsList[1]):
            if self.RunLoud:
                print('Western limit different from eastern')
        else:
            print('ERROR western limit {} is the same as eastern {}'.format(BoundsList[0], BoundsList[1]))
            return False

        # West limit should be somewhere on earth and west of eastern limit (but the sphere is continuous so...)
        if (BoundsList[0] >= -180.0) and (BoundsList[0] <= 180.0) and (BoundsList[0] != BoundsList[1]):
            if self.RunLoud:
                print('Western limit is good')
        else:
            print('ERROR with Western limit {}'.format(BoundsList[0]))
            return False

        # East limit should be somewhere on earth and east of western limit (but the sphere is continuous so...)
        if (BoundsList[1] >= -180.0) and (BoundsList[1] <= 180.0) and (BoundsList[0] != BoundsList[1]):
            if self.RunLoud:
                print('Eastern limit is good')
        else:
            print('ERROR with eastern limit {}'.format(BoundsList[1]))
            return False

        if BoundsList[0] <  BoundsList[1]:
            if self.RunLoud:
                print('Does not cross dateline')
            BoundsIncDateline = False
        else:
            if self.RunLoud:
                print('Bounds include the dateline. Now things are complicated')
            BoundsIncDateline = True


        if self.RunLoud:
            print("Limits are W: {} E: {} S: {} N: {} Dateline crossed: {}".format(args.Bounds[0],args.Bounds[1],args.Bounds[2],args.Bounds[3],BoundsIncDateline))
        return True


    # Functions
    def CheckExtension(self, ExtString):
        if (os.path.exists(self.InputFile[:-3]+ExtString.lower())) or (os.path.exists(self.InputFile[:-3]+ExtString.upper())):
            if self.RunLoud:
                print(self.InputFile[:-3]+ExtString, " - exists")
        else:
            print(self.InputFile[:-3]+ExtString, " - is missing and will be needed by ogr2ogr.")
            print("HydroSHEDS distributes .shp, .dbf, .prj, and .shx files in the same zip file. \nThey should be kept in the same directory.\nExiting")
            exit(8)

    def ParseUpstreamCells(self, line):
        """
        Parse Upstream Cells 
        Takes a full comment line as input and looks for the count of upstream cells.
    
        Expected format 
        # @D1|121
    
        Exception if it cannot find the count.
        """
        # Find the | and get the integer after it
        i = line.find("|")
        if i == -1:
            raise UpstreamCountError(line, '| not found')
    
        UpstreamCellsStr = line[i+1:].strip()
        if not UpstreamCellsStr.isdigit():
            if self.RunLoud:
                print("Error non digits where only digits expected")
                print(UpstreamCellsStr)
            raise UpstreamCountError(line, 'chars after | not digits')
        
        try:
            UpstreamCells = int(UpstreamCellsStr)
        except ValueError as err:
            if self.RunLoud:
                print("ValueError in converting upstream cells count to int")
                print(UpstreamCellsStr)
                print(err)
                print("Will attempt to continue")
            raise UpstreamCountError(line, 'unable to convert with int({})'.format(UpstreamCellsStr))
    
        return UpstreamCells
    
    def UpstreamCellsWithinLimits(self, UpstreamCount):
        """
        Checks the upstream count against thresholds
        """
        if UpstreamCount < self.MinUpstream:
            return False
        elif UpstreamCount > self.MaxUpstream:
            return False
        else:
            return True
        
    # TODO Not called - verify and remove
    def RangeIncDateline(self, Wlimit,Elimit):
        if Wlimit <  Elimit:
            if self.RunLoud:
                print('Does not cross dateline')
            BoundsIncDateline = False
        else:
            if self.RunLoud:
                print('Bounds include the dateline. Now things are complicated')
            BoundsIncDateline = True
        
        return BoundsIncDateline

    #def PointWithinBoundry(Lat,Lon,Wlimit,Elimit,Slimit,Nlimit):
    def PointWithinBoundry(self, Lat,Lon,Bounds):
        if isinstance(Bounds, list) and (len(Bounds) == 5 ):
            Wlimit = Bounds[0]
            Elimit = Bounds[1]
            Slimit = Bounds[2]
            Nlimit = Bounds[3]
            BoundsIncDateline = Bounds[4]
        else:
            print('ERROR bounds in PointWithinBoundry not valid')
            exit(8)
        
        #print(Lat,Lon,Wlimit,Elimit,Slimit,Nlimit)

        #BoundsIncDateline = self.RangeIncDateline(Wlimit,Elimit)
    
        if (Lat <= Nlimit) and (Lat >= Slimit):
            # In the limit, check longitude 
            pass
        else:
            #print("Lat out of limit")
            return False

    
        if not BoundsIncDateline:
            if (Lon <= Elimit) and (Lon >= Wlimit):
                return True
            else:
                return False
        else:
            # split across International Dateline
            if (Lon >= Wlimit) and (Lon <= 180.0):
                return True
            elif (Lon >= -180.0) and (Lon <= Elimit):
                return True
            else:
                return False

    def CheckBounds(self, Lat,Lon):
        #global CopyWithinBounds - old
        #global SimpleBounds - old
        
    
        if self.CopyWithinBounds is not False:
            if self.CopyWithinBounds is True:
                # Simple boundaries
                if self.SimpleBounds is not None:
                    return self.PointWithinBoundry(Lat,Lon,self.SimpleBounds)
                
                # TODO Add bounds file support
                # It will not be and else. We support both simple and file bounds in same command - to return True must be in both bounds
        else:
            #print("Just returning true (Error if bounds set)")
            return True

    def CreatePenWidth(self, UpstreamCount):
        """
        Returns the appropriate pen width with units as a string
        """
        return "0.25p"

    def CreatePenColour(self, UpstreamCount):
        """
        Returns the appropriate pen colour as a string
        """
        return "255/0/0"
    
    
    def CreateSegmentHeader(self, UpstreamCount):
        """
        Create Segment Header
        Takes the count of upstream cells and returns a line starting with > and
        continuing with any special additions.
    
        Expected integer
    
        """
        return "> -W0.25p,red \n"
    
        if(self.PenColour is not None) and (self.PenWidth is not None):
            SegmentHeaderStr = "> -W{},{} \n".format(self.CreatePenWidth(UpstreamCount),self.CreatePenColour(UpstreamCount))
        elif(self.PenColour is None):
            SegmentHeaderStr = "> -W{} \n".format(self.CreatePenWidth(UpstreamCount))
        elif(self.PenWidth is None):
            SegmentHeaderStr = "> -W{} \n".format(self.CreatePenColour(UpstreamCount))
        else:
            #This should never happen
            print("Error in CreateSegmentHeader unexpected args")
            exit(21)
    
        return SegmentHeaderStr

    def SummarizeGMTFile(self, FileName):
        """
        Returns a dictionary with the number of segments, largest, and smallest upstream counts.
        """
    
        if self.OutputForHistogram:
            HistFileName = FileName[:-4] + '_UpCounts.txt'
            if (os.path.exists(HistFileName)) and (not self.Overwrite):
                print("File exists. Use -o to overwrite. Exiting")
                exit(9)
            
            CountsFile = open(HistFileName, 'w')
    
        CountLines = 0
        CountSegments = 0
        SmallestUpstreamCells = 10000000000
        LargestUpstreamCells = 0
        ErrorCount = 0
    
        SegmentHeaderFound = False
    
        with open(FileName, 'r') as InFile:
            for line in InFile:
                CountLines += 1
            
                if SegmentHeaderFound:
                    SegmentHeaderFound = False
                    CountSegments += 1
        
                    try:
                        UpstreamCells = self.ParseUpstreamCells(line)
                    except UpstreamCountError as err:
                        if not self.RunSilent:
                            print("Error in SummarizeGMTFile \nunable to parse comment on line {}. Continuing.".format(CountLines))
                            print(err)
                        ErrorCount += 1
                    else:
                    #Keep track of largest and smallest upstream - if no exception and write to file if -hist
                        if UpstreamCells > LargestUpstreamCells:
                            LargestUpstreamCells = UpstreamCells
                        if UpstreamCells < SmallestUpstreamCells:
                            SmallestUpstreamCells = UpstreamCells
                        if self.OutputForHistogram:
                            CountsFile.write("{}\n".format(UpstreamCells))
                        
            
    
                if line[0] == ">":
                    SegmentHeaderFound = True
                
        if self.OutputForHistogram:
            CountsFile.close()
            if self.RunLoud:
                print("Each upstream count saved in ")
                print(HistFileName)
    
        if self.RunLoud:
            print("SummarizeGMTFile found {} lines and {} segments".format(CountLines,CountSegments))
            print("The largest and smallest upstream cells counts were {} and {}".format(LargestUpstreamCells,SmallestUpstreamCells))
            print("There were {} errors - segments that could not be parsed".format(ErrorCount))
        
        return {'CountLines': CountLines, 
                'CountSegments': CountSegments ,
                'SmallestUpstreamCells': SmallestUpstreamCells, 
                'LargestUpstreamCells': LargestUpstreamCells, 
                'ErrorCount': ErrorCount}

    # Begin Main Program
    def ParseRIV(self):

        # If .shp input, convert using ogr2ogr from GDAL. Exit with error if ogr2ogr is not accessable.
        InputExtension = self.InputFile[-3:]
        if self.RunLoud:
            print("InputFile extension is", InputExtension)

        if (InputExtension == "shp") or (InputExtension == "SHP"):
            if self.RunLoud:
                print("Converting to gmt type file with GDAL ogr2ogr")
        
            #ogr2ogr expects an shx file
            # It also needs dbf and prj files but will silently produce undesired output if not provided
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
                ExitStatus = os.system(CommandString)
            except OSError as err:
                print(" Error unable to run ",CommandString)
                print("OSError")
                print(err)
                if self.RunLoud:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_tb(exc_traceback)
                exit(11)
            except:
                print(" Error unable to run ",CommandString)
                print("We have no idea why it failed. Exiting")
                if self.RunLoud:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_tb(exc_traceback)
                exit(12)
        
            if self.RunLoud:
                print("ogr2ogr exit status: ",ExitStatus)
                print("\n")
            if ExitStatus != 0:
                print("ogr2ogr appears to have failed.\nIt may be that you need to open GMT to access GDAL ogr2ogr. \nExiting")
                exit(13)
    
        
        elif (InputExtension == "gmt") or (InputExtension == "GMT"):
            if self.RunLoud:
                print("File type is gmt")
    
            self.InFileGMTtxt = self.InputFile
    
        else:
            print("\nError input file type not supported. \nSupported extensions are: ",SUPPORTED_INPUT_EXTENSIONS)
            exit(7)

        # If specified parse the file for the largest and smallest upstream count
        if self.OutputForHistogram:
            FileSummary = self.SummarizeGMTFile(self.InFileGMTtxt)

        # Move down the input file line by Line
        InFile = open(self.InFileGMTtxt, 'r')
        OutFile = open(self.OutputFile, 'w')

        CountLines = 0
        CountSegments = 0
        CountSegmentsCopied = 0
        SmallestUpstreamCells = 10000000000
        LargestUpstreamCells = 0

        SegmentHeaderFound = False
        SkipThisSegment = False
        AboutToCopyFirstSegmentLine = False

        SavedCommentLine = ''

        for line in InFile:
            CountLines += 1
    
            # After each segment header > line look for a comment line of the format 
            # @A###|###
            # The integer after the | is a count of upstream cells
            if SegmentHeaderFound:
                SegmentHeaderFound = False
                CountSegments += 1
        
                try:
                    UpstreamCells = self.ParseUpstreamCells(line)
                except UpstreamCountError as err:
                    if not self.RunSilent:
                        print("Error unable to parse comment on line {}. Continuing.".format(CountLines))
                        print(err)
                    UpstreamCells = 0
                else:
                    #Keep track of largest and smallest upstream - if no exception
                    if UpstreamCells > LargestUpstreamCells:
                        LargestUpstreamCells = UpstreamCells
                    if UpstreamCells < SmallestUpstreamCells:
                        SmallestUpstreamCells = UpstreamCells
            
                # If TL or TH are set we only want to 
                # If the count is between thresholds 
                #  Output a new segment header > with proper -W pen options
                # If the count is out of threshold, skip this segment and look for the next One
                if self.UpstreamCellsWithinLimits(UpstreamCells):
                    CountSegmentsCopied += 1
                    SkipThisSegment = False
                    AboutToCopyFirstSegmentLine = True
            
                else:
                    SkipThisSegment = True
            
            # Skip line if only white space (\n etc)
            if line.isspace():
                pass
    
            # Skip segment headers and set flag to add them back.
            elif line[0] == ">":
                SegmentHeaderFound = True
        
            # Skip segments including comment lines if previously identified for skipping
            elif SkipThisSegment:
                pass
        
            # Reproduce each comment line as is
            elif line[0] == "#":
                if AboutToCopyFirstSegmentLine:
                    SavedCommentLine = line
                else:
                    OutFile.write(line)
    
            
    
            # check for in bounds on first line if enabled
            elif line[1].isdigit() and AboutToCopyFirstSegmentLine:
                # If any bounding is set
                if self.CopyWithinBounds is not False:
                    AboutToCopyFirstSegmentLine = False
        
                    # Order in gmt files is Lon Lat 142.245833333334 -10.133333333333
                    Lon,Lat = line.split()
                    Lat = float(Lat)
                    Lon = float(Lon)
        
                    if self.CheckBounds(Lat,Lon):
            
                        if self.SegmentHeaderIsSimple:
                            OutFile.write(">\n")
                        else:
                            OutFile.write(self.CreateSegmentHeader(UpstreamCells))
                
                        OutFile.write(SavedCommentLine)
                        OutFile.write(line)
                    else:
                        SkipThisSegment = True
                
                # else no bounding is set
                else:
                    AboutToCopyFirstSegmentLine = False
            
                    if self.SegmentHeaderIsSimple:
                        OutFile.write(">\n")
                    else:
                        OutFile.write(self.CreateSegmentHeader(UpstreamCells))
            
                    OutFile.write(SavedCommentLine)
                    OutFile.write(line)
                    

    
            #  Reproduce each data line as is. The first character might be a minus. 
            elif line[1].isdigit():
                OutFile.write(line)
    
            else:
                if not self.RunSilent:
                    print("Warning unexpected line start. Skipping line {}".format(CountLines))
                    print(line)


        # Close input and output files at EOF
        InFile.close()
        OutFile.close()

        if self.RunLoud:
            print("\n\n")
            print('There were {} lines in the file.'.format(CountLines))
            print('There were {} segments in the file.'.format(CountSegments))
            print('There were {} segments copied to the output file.'.format(CountSegmentsCopied))
            print('The upstream cells count ranged from {} to {}.'.format(SmallestUpstreamCells,LargestUpstreamCells))
        # Report count of segments in input and segments in output
        # Report range of upstream cells in input and output

        if not self.RunSilent:
            print("complebitur")
        if self.RunLoud:
            print("\n\n")


if __name__ == "__main__":
    print("Running Parse SHEDS riv as __main__")
    
    import argparse
    
    # Receive calling Parameters
    parser = argparse.ArgumentParser(description='Parse HydroSHEDS River Network files for GMT')
    parser.add_argument("-d", "--detailedinfo", action="store_true",
                        help="Print detailed script info and exit")
    parser.add_argument("-hp", "--HelpPen", action="store_true",
                        help="Print detailed pen options help (-p) and exit")
    parser.add_argument('--version', action='version',
                        version="%(prog)s {}".format(__version__))
                    
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Increase output verbosity")
    parser.add_argument("-s", "--silent", action="store_true",
                        help="Run without terminal output except for program failure. Overridden by verbose")
                    
    parser.add_argument("-o", "--Overwrite", action="store_true",
                        help="Overwrite exisiting output. Default is to exit if OutputFile exists.")
    parser.add_argument("-hist", "--OutputForHistogram", action="store_true",
                        help="Output the upstream counts is a separate file for creating histograms")

    parser.add_argument("-TH", "-th", "--ThresholdHigh", action="store", type=int,
                        help="The high threshold for upstream count. Values above this are omitted.")
    parser.add_argument("-TL", "-tl", "--ThresholdLow", action="store", type=int,
                        help="The low threshold for upstream count. Values below this are omitted.")
    parser.add_argument("-pc", "--PenColour", action="store",
                        help="Set pen colour which will be added to segment header. -hp for details.")
    parser.add_argument("-pw", "--PenWidth", action="store",
                        help="Set pen width which will be added to segment header. -hp for details.")
                    
    parser.add_argument("-B", "-b", "--Bounds", action="store", nargs=4, type=float,
                        help="Set limits on which segments to output based on location.\nOnly the first point in the segment will be checked. Others may leave the boundry.\nFormat: -b W E S N \nUse decimal notation and - for south and west.")
                    
    parser.add_argument("InputFile", action="store", nargs=1, 
                        help="Name of input file. Either relative or full path.")
    parser.add_argument("OutputFile", action="store", nargs=1, 
                        help="Name of output file. Either relative or full path.")

    args = parser.parse_args()


    # Bring in flags and run some initial tests
    if args.detailedinfo:
        print(__doc__)
        exit(0)

    if args.HelpPen:
        print(PEN_HELP_TEXT)
        exit(0)

    if args.verbose is True:
        RUN_LOUD = True
    else:
        RUN_LOUD = False

    if RUN_LOUD:
        print("RUN_LOUD true")
        RUN_SILENT = False
    elif args.silent is True:
        RUN_SILENT = True
    else:
        RUN_SILENT = False
        
    if args.OutputForHistogram is True:
        OUTPUT_UPSTREAM_COUNTS = True
        if RUN_LOUD:
            print("A seporate file with each upstream count will be output")
    else:
        OUTPUT_UPSTREAM_COUNTS = False


    if not RUN_SILENT:
        print("\nParse SHEDS riv Starting\n\n")
        print("The HydroSHEDS license requires atribution. \nSee https://www.hydrosheds.org/page/license\n\n")
        if (args.ThresholdHigh is None) and (args.ThresholdLow is None) and (args.PenColour is None) and (args.PenWidth is None):
            print("Warning without some sort of direction this program will change nothing. (needs -TH, -TL, etc)\n")
    

    if (args.Overwrite is True):
        OVERWRITE_FILES = True
        if RUN_LOUD:
            print("Warning will overwrite OutputFile if it exists")
    else:
        OVERWRITE_FILES = False

    # Check for infile, outfile
    if RUN_LOUD:
        print("Checking if files exist")
    INPUT_FILE = args.InputFile[0]
    if os.path.exists(INPUT_FILE):
        if RUN_LOUD:
            print(INPUT_FILE,'  - exists')
    else:
        print("No input file found - ",INPUT_FILE)
        exit(5)

    OUTPUT_FILE = args.OutputFile[0]
    if (os.path.exists(OUTPUT_FILE)) and (OVERWRITE_FILES is not True):
        print(OUTPUT_FILE,'  - exists \nUse -o to overwrite \nExiting')
        exit(6)

    # Thresholds are expected and thus set to low and high values if not set
    if args.ThresholdHigh is not None:
        MAX_UPSTREAM = args.ThresholdHigh
        if not RUN_SILENT:
            print("MAX_UPSTREAM set to ", MAX_UPSTREAM)
    else:
        MAX_UPSTREAM = 100000000000   # Intended to be so large it is never an issue
    
    if args.ThresholdLow is not None:
        MIN_UPSTREAM = args.ThresholdLow
        if not RUN_SILENT:
            print("MIN_UPSTREAM set to ", MIN_UPSTREAM)
    else:
        MIN_UPSTREAM = -1

    # If nothing special is set with the pen, the header will be a simple >
    if (args.PenColour is None) and (args.PenWidth is None):
        SEGMENT_HEADER_IS_SIMPLE = True
    else:
        SEGMENT_HEADER_IS_SIMPLE = False
    
    if args.Bounds is not None:
        CopyWithinBounds = True
        # Check Lat
        if (args.Bounds[2] < args.Bounds[3]):
            if RUN_LOUD:
                print('Southern limit is south of northern')
        else:
            print('ERROR southern limit {} is not south of northern {}'.format(args.Bounds[2], args.Bounds[3]))
            exit(7)
    
        
        # Southern limit should be somewhere on earth and south of northern limit
        if (args.Bounds[2] >= -90.0) and (args.Bounds[2] <= 90.0):
            if RUN_LOUD:
                print('Southern limit is good')
        else:
            print('ERROR with southern limit {}'.format(args.Bounds[2]))
            exit(7)
    
        # Northern limit should be somewhere on earth and north of Southern limit
        if (args.Bounds[3] >= -90.0) and (args.Bounds[3] <= 90.0):
            if RUN_LOUD:
                print('Northern limit is good')
        else:
            print('ERROR with northern limit {}'.format(args.Bounds[3]))
            exit(7)
        
        # Check Lon
        if (args.Bounds[0] != args.Bounds[1]):
            if RUN_LOUD:
                print('Western limit different from eastern')
        else:
            print('ERROR western limit {} is the same as eastern {}'.format(args.Bounds[0], args.Bounds[1]))
            exit(7)
    
        # West limit should be somewhere on earth and west of eastern limit (but the sphere is continuous so...)
        if (args.Bounds[0] >= -180.0) and (args.Bounds[0] <= 180.0) and (args.Bounds[0] != args.Bounds[1]):
            if RUN_LOUD:
                print('Western limit is good')
        else:
            print('ERROR with Western limit {}'.format(args.Bounds[0]))
            exit(7)
    
        # East limit should be somewhere on earth and east of western limit (but the sphere is continuous so...)
        if (args.Bounds[1] >= -180.0) and (args.Bounds[1] <= 180.0) and (args.Bounds[0] != args.Bounds[1]):
            if RUN_LOUD:
                print('Eastern limit is good')
        else:
            print('ERROR with eastern limit {}'.format(args.Bounds[1]))
            exit(7)

        if args.Bounds[0] <  args.Bounds[1]:
            if RUN_LOUD:
                print('Does not cross dateline')
            BoundsIncDateline = False
        else:
            if RUN_LOUD:
                print('Bounds include the dateline. Now things are complicated')
            BoundsIncDateline = True
    
        if not RUN_SILENT:
            print("Limits are W: {} E: {} S: {} N: {} Dateline crossed: {}".format(args.Bounds[0],args.Bounds[1],args.Bounds[2],args.Bounds[3],BoundsIncDateline))
    
    
        # Class init expects 4 floats in bounds list. Dateline added later
        #SimpleBounds = args.Bounds.copy()
        #print(SimpleBounds)
        #SimpleBounds.append(BoundsIncDateline)
        #print(SimpleBounds)
    
    else:
        # args.Bounds is None
        CopyWithinBounds = False
    
    #print(SimpleBounds)
    

    # Now we can do things

    try:
        RIVParser = SHEDSrivParser(INPUT_FILE,
                                    OUTPUT_FILE,
                                    ThresholdHigh=MAX_UPSTREAM, 
                                    ThresholdLow=MIN_UPSTREAM, 
                                    PenColour=args.PenColour, 
                                    PenWidth=args.PenWidth, 
                                    SimpleBounds=args.Bounds,
                                    BoundsFile=None,
                                    RunLoud=RUN_LOUD, 
                                    RunSilent=RUN_SILENT, 
                                    OutputForHistogram=OUTPUT_UPSTREAM_COUNTS, 
                                    Overwrite=OVERWRITE_FILES)
    except InitInputError as err:
        print("ERROR - FAIL")
        print(err.message)
        exit(15)
    
    #try:
    RIVParser.ParseRIV()
    #except:
    #    print("ERROR - Fail")
    #    exit(16)
        
    exit(0)
