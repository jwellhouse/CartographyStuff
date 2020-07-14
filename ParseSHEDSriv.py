"""
Parse SHEDS riv is a Python script to parse HydroSHEDS river network (riv) data for GMT.

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
Last Update: 2020-07-13
"""

__version__ = "0.0.2"
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

import argparse
import os
import traceback
import sys

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


# Functions
def CheckExtension(ExtString):
    if (os.path.exists(INPUT_FILE[:-3]+ExtString.lower())) or (os.path.exists(INPUT_FILE[:-3]+ExtString.upper())):
        if RUN_LOUD:
            print(INPUT_FILE[:-3]+ExtString, " - exists")
    else:
        print(INPUT_FILE[:-3]+ExtString, " - is missing and will be needed by ogr2ogr.")
        print("HydroSHEDS distributes .shp, .dbf, .prj, and .shx files in the same zip file. \nThey should be kept in the same directory.\nExiting")
        exit(8)

def ParseUpstreamCells(line):
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
        if RUN_LOUD:
            print("Error non digits where only digits expected")
            print(UpstreamCellsStr)
        raise UpstreamCountError(line, 'chars after | not digits')
        
    try:
        UpstreamCells = int(UpstreamCellsStr)
    except ValueError as err:
        if RUN_LOUD:
            print("ValueError in converting upstream cells count to int")
            print(UpstreamCellsStr)
            print(err)
            print("Will attempt to continue")
        raise UpstreamCountError(line, 'unable to convert with int({})'.format(UpstreamCellsStr))
    
    return UpstreamCells
    
def UpstreamCellsWithinLimits(UpstreamCount):
    """
    Checks the upstream count against thresholds
    """
    if UpstreamCount < MIN_UPSTREAM:
        return False
    elif UpstreamCount > MAX_UPSTREAM:
        return False
    else:
        return True

def CreatePenWidth(UpstreamCount):
    """
    Returns the appropriate pen width with units as a string
    """
    return "0.25p"

def CreatePenColour(UpstreamCount):
    """
    Returns the appropriate pen colour as a string
    """
    return "255/0/0"
    
    
def CreateSegmentHeader(UpstreamCount):
    """
    Create Segment Header
    Takes the count of upstream cells and returns a line starting with > and
    continuing with any special additions.
    
    Expected integer
    
    """
    return "> -W0.25p,red \n"
    
    if(args.PenColour is not None) and (args.PenWidth is not None):
        SegmentHeaderStr = "> -W{},{} \n".format(CreatePenWidth(UpstreamCount),CreatePenColour(UpstreamCount))
    elif(args.PenColour is None):
        SegmentHeaderStr = "> -W{} \n".format(CreatePenWidth(UpstreamCount))
    elif(args.PenWidth is None):
        SegmentHeaderStr = "> -W{} \n".format(CreatePenColour(UpstreamCount))
    else:
        #This should never happen
        print("Error in CreateSegmentHeader unexpected args")
        exit(21)
    
    return SegmentHeaderStr

def SummarizeGMTFile(FileName):
    """
    Returns a dictionary with the number of segments, largest, and smallest upstream counts.
    """
    
    if OUTPUT_UPSTREAM_COUNTS:
        HistFileName = FileName[:-4] + '_UpCounts.txt'
        if (os.path.exists(HistFileName)) and (not OVERWRITE_FILES):
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
                    UpstreamCells = ParseUpstreamCells(line)
                except UpstreamCountError as err:
                    if not RUN_SILENT:
                        print("Error in SummarizeGMTFile \nunable to parse comment on line {}. Continuing.".format(CountLines))
                        print(err)
                    ErrorCount += 1
                else:
                #Keep track of largest and smallest upstream - if no exception and write to file if -hist
                    if UpstreamCells > LargestUpstreamCells:
                        LargestUpstreamCells = UpstreamCells
                    if UpstreamCells < SmallestUpstreamCells:
                        SmallestUpstreamCells = UpstreamCells
                    if OUTPUT_UPSTREAM_COUNTS:
                        CountsFile.write("{}\n".format(UpstreamCells))
                        
            
    
            if line[0] == ">":
                SegmentHeaderFound = True
                
    if OUTPUT_UPSTREAM_COUNTS:
        CountsFile.close()
        if RUN_LOUD:
            print("Each upstream count saved in ")
            print(HistFileName)
    
    if RUN_LOUD:
        print("SummarizeGMTFile found {} lines and {} segments".format(CountLines,CountSegments))
        print("The largest and smallest upstream cells counts were {} and {}".format(LargestUpstreamCells,SmallestUpstreamCells))
        print("There were {} errors - segments that could not be parsed".format(ErrorCount))
        
    return {'CountLines': CountLines, 
            'CountSegments': CountSegments ,
            'SmallestUpstreamCells': SmallestUpstreamCells, 
            'LargestUpstreamCells': LargestUpstreamCells, 
            'ErrorCount': ErrorCount}

# Begin Main Program

# If .shp input, convert using ogr2ogr from GDAL. Exit with error if ogr2ogr is not accessable.
InputExtension = INPUT_FILE[-3:]
if RUN_LOUD:
    print("InputFile extension is", InputExtension)

if (InputExtension == "shp") or (InputExtension == "SHP"):
    if RUN_LOUD:
        print("Converting to gmt type file with GDAL ogr2ogr")
        
    #ogr2ogr expects an shx file
    # It also needs dbf and prj files but will silently produce undesired output if not provided
    CheckExtension('shx')
    CheckExtension('dbf')
    CheckExtension('prj')
    
    IntermediateFileName = INPUT_FILE[:-4] + '_TempConv.gmt'
    InFileGMTtxt = IntermediateFileName
    if RUN_LOUD:
        print("Will create temporary intermediate file\n  {}".format(IntermediateFileName))
    
    
    # Call ogr2ogr GDAL
    if RUN_LOUD:
        CommandString = 'ogr2ogr -f "GMT" ' + IntermediateFileName + ' ' + INPUT_FILE + ' --debug ON'
    elif not RUN_SILENT:
        CommandString = 'ogr2ogr -f "GMT" ' + IntermediateFileName + ' ' + INPUT_FILE 
    else:
        CommandString = 'ogr2ogr -f "GMT" ' + IntermediateFileName + ' ' + INPUT_FILE + ' --debug OFF >/dev/null 2>&1'
    
    try:
        if RUN_LOUD:
            print("Running: ", CommandString, "\n")
        ExitStatus = os.system(CommandString)
    except OSError as err:
        print(" Error unable to run ",CommandString)
        print("OSError")
        print(err)
        if RUN_LOUD:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback)
        exit(11)
    except:
        print(" Error unable to run ",CommandString)
        print("We have no idea why it failed. Exiting")
        if RUN_LOUD:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback)
        exit(12)
        
    if RUN_LOUD:
        print("ogr2ogr exit status: ",ExitStatus)
        print("\n")
    if ExitStatus != 0:
        print("ogr2ogr appears to have failed.\nIt may be that you need to open GMT to access GDAL ogr2ogr. \nExiting")
        exit(13)
    
        
elif (InputExtension == "gmt") or (InputExtension == "GMT"):
    if RUN_LOUD:
        print("File type is gmt")
    
    InFileGMTtxt = INPUT_FILE
    
else:
    print("\nError input file type not supported. \nSupported extensions are: ",SUPPORTED_INPUT_EXTENSIONS)
    exit(7)

# If specified parse the file for the largest and smallest upstream count
if OUTPUT_UPSTREAM_COUNTS:
    FileSummary = SummarizeGMTFile(InFileGMTtxt)

# Move down the input file line by Line
InFile = open(InFileGMTtxt, 'r')
OutFile = open(OUTPUT_FILE, 'w')

CountLines = 0
CountSegments = 0
CountSegmentsCopied = 0
SmallestUpstreamCells = 10000000000
LargestUpstreamCells = 0

SegmentHeaderFound = False
SkipThisSegment = False

for line in InFile:
    CountLines += 1
    
    # After each segment header > line look for a comment line of the format 
    # @A###|###
    # The integer after the | is a count of upstream cells
    if SegmentHeaderFound:
        SegmentHeaderFound = False
        CountSegments += 1
        
        try:
            UpstreamCells = ParseUpstreamCells(line)
        except UpstreamCountError as err:
            if not RUN_SILENT:
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
        if UpstreamCellsWithinLimits(UpstreamCells):
            CountSegmentsCopied += 1
            SkipThisSegment = False
            
            if SEGMENT_HEADER_IS_SIMPLE:
                OutFile.write(">\n")
            else:
                OutFile.write(CreateSegmentHeader(UpstreamCells))
        else:
            SkipThisSegment = True
            
    
    # Skip segment headers and set flag to add them back.
    if line[0] == ">":
        SegmentHeaderFound = True
        
    # Skip segments including comment lines
    elif SkipThisSegment:
        pass
        
    # Reproduce each comment line as is
    elif line[0] == "#":
        OutFile.write(line)
    
    #  Reproduce each data line as is. The first character might be a minus. 
    elif line[1].isdigit():
        OutFile.write(line)
    
    else:
        if not RUN_SILENT:
            print("Warning unexpected line start. Skipping line {}".format(CountLines))
            print(line)


# Close input and output files at EOF
InFile.close()
OutFile.close()

if RUN_LOUD:
    print("\n\n")
    print('There were {} lines in the file.'.format(CountLines))
    print('There were {} segments in the file.'.format(CountSegments))
    print('There were {} segments copied to the output file.'.format(CountSegmentsCopied))
    print('The upstream cells count ranged from {} to {}.'.format(SmallestUpstreamCells,LargestUpstreamCells))
# Report count of segments in input and segments in output
# Report range of upstream cells in input and output

if not RUN_SILENT:
    print("complebitur")
if RUN_LOUD:
    print("\n\n")
exit(0)
