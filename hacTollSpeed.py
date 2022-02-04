#!/usr/bin/env python3

import sys
try:
    assert (sys.version_info.major == 3 and sys.version_info.minor >= 7), "Python version must be 3.7 or newer"
except Exception as e:
    print (e)
    sys.exit(1)

import os
from os import environ
from urllib.parse import _NetlocResultMixinStr
import xlrd
from enum import Enum
from datetime import datetime
import pdb
from hacGpsPoints import HAC_gpsPoints, HAC_gpsPoints_Error
from tomtomLookup import TomTomLookup
import json
import logging
import argparse
import xlsxwriter

# check if debugging requested via environment variable DEBUG
try:
    DEBUG = int(environ.get('DEBUG'))
except:
    DEBUG = 0

try:
    TOMTOM_AUTH_KEY = environ.get('TOMTOM_AUTH_KEY')
    assert (len(TOMTOM_AUTH_KEY) > 1), "Environment variable TOMTOM_AUTH_KEY length too short"
except:
    print("Environment variable TOMTOM_AUTH_KEY not defined", file=sys.stderr)
    sys.exit(1)
 

class HAC_Sheet(Enum):
    """ Stupci u worksheetu koji nas zanimaju """
    col_Relacija        = 1
    col_Tip_transakcije = 2
    col_Vrijeme_ulaska  = 4
    col_Vrijeme_izlaska = 5
    col_Uplata_HRK      = 8
    col_Isplata_HRK     = 9

# some global variables comes handy here
header_rownum = None

def rootLoggerFilename():
    rootlogger = logging.getLogger()
    for handler in rootlogger.handlers:
        if hasattr(handler, "baseFilename"):
            return getattr(handler, 'baseFilename')


def obj_dump_as_list(obj):
    # here we use a list comprehension, a true pythonic way of doing things iterable
    return ["'{}'={}".format(attr, repr(getattr(obj, attr))) for attr in dir(obj) if not attr.startswith("__") ]


def validate_format(worksheet):
    """
    Excel sheet format validation
    """
    global header_rownum

    # Find where transactions begin
    for rownum in range(0, worksheet.nrows):
        if ('Relacija' == worksheet.cell_value(rownum, HAC_Sheet.col_Relacija.value)):
            header_rownum = rownum
            break

    if header_rownum is None:
        raise HAC_gpsPoints_Error("Invalid data format")

    if False:
        for colnum in range(1, worksheet.ncols):
            if worksheet.cell_value(header_rownum, colnum):
                print('Column {} = {}'.format(colnum, repr(worksheet.cell_value(header_rownum, colnum))))

    if (    worksheet.cell_value(header_rownum, HAC_Sheet.col_Tip_transakcije.value) == 'Tip transakcije' and
            worksheet.cell_value(header_rownum, HAC_Sheet.col_Vrijeme_ulaska.value)  == 'Vrijeme ulaska'  and
            worksheet.cell_value(header_rownum, HAC_Sheet.col_Vrijeme_izlaska.value) == 'Vrijeme izlaska' and
            worksheet.cell_value(header_rownum, HAC_Sheet.col_Uplata_HRK.value)      == 'Uplata (HRK)'    and
            worksheet.cell_value(header_rownum, HAC_Sheet.col_Isplata_HRK.value)     == 'Isplata (HRK)'   and
        True ):
        return True
    else:
        raise HAC_gpsPoints_Error("Invalid data format")


def hac_date(date_str):
    # 08.01.2022 18:59:22
    return datetime.strptime(date_str, r'%d.%m.%Y %H:%M:%S')

# convert comma-decimal to floating point number
def hrk_value(num_str):
    return float(num_str.replace(',', '.'))


def tomtom_url(gps_od, gps_do):
    def prefix():
        return 'https://api.tomtom.com/routing/1/calculateRoute/'
    def suffix():
        return (f'/json?key={TOMTOM_AUTH_KEY}&routeRepresentation=summaryOnly&maxAlternatives=0' + 
                '&computeTravelTimeFor=none&routeType=fastest&traffic=false&travelMode=car')
    return f'{prefix()}{",".join(gps_od)}:{",".join(gps_do)}{suffix()}'

ttl = TomTomLookup() # global
def tomtom_getDistance(url):
    global ttl
    return ttl.getDistance(url)


def humanize_time(amount):    

    def process_time(amount):
        IVALS = [ 1,   60,  60*60 ] 
        NAMES = [ 's', 'm', 'h'   ]
        result = []

        for i in range(len(NAMES)-1, -1, -1):
            a = amount // IVALS[i]
            if a > 0: 
                result.append( (a, NAMES[i]) )
                amount -= a * IVALS[i]
        return result

    buf = ''
    for u in process_time(int(amount)):
        if u[0] > 0:
            buf += "%d%s " % (u[0], u[1])
    
    return buf.rstrip()


def scan_worksheet(worksheet, xlsx_out_fn, json_out_fn):
    """
    We go through workbook looking for rows we're interested in
    """
    global header_rownum
    # pdb.set_trace()

    # tracking unique set of entry and exit points
    # (never seen before - missing from the CSV)
    missing_topo_ul = set() # entry points
    missing_topo_iz = set() # exit points
    missing_topo    = set() # whole record missing

    try:
        os.remove(xlsx_out_fn)
    except:
        pass

    # create the JSON output file for writing
    of = open(json_out_fn, 'w', encoding="utf-8")
    of.truncate()

    # create the Excel output file for writing
    owb = xlsxwriter.Workbook(xlsx_out_fn)
    ows = owb.add_worksheet()

    # header row formats
    th_format = owb.add_format({'bold': True, 'align': 'left', 'bg_color': '#808080', 'font_color': '#FFFFFF'})
    th_format_num = owb.add_format({'bold': True, 'align': 'right', 'bg_color': '#808080', 'font_color': '#FFFFFF'})
    
    # column widths (unit: character)
    ows.set_column(0, 1, 30) # od-do
    ows.set_column(2, 3, 24) # vrijeme od-do
    ows.set_column(4, 4, 14) # vrijeme sec
    ows.set_column(5, 5, 16) # vrijeme h:m:s
    ows.set_column(6, 7, 22) # distance & speed
    ows.set_column(8, 8, 22) # cestarina
    
    # numerical cell formats
    num_format = owb.add_format({ 'align': 'right', 'num_format': '#,##0.0' })
    hrk_format = owb.add_format({ 'align': 'right', 'num_format': '#,##0.00 kn' })
    hms_format = owb.add_format({ 'align': 'right' })
    
    # output the header row
    row_out = 0
    ows.write(row_out, 0, "Ulaz", th_format)
    ows.write(row_out, 1, "Izlaz", th_format)
    ows.write(row_out, 2, "Vrijeme ulaska", th_format)
    ows.write(row_out, 3, "Vrijeme izlaska", th_format)
    ows.write(row_out, 4, "Trajanje (s)", th_format_num)
    ows.write(row_out, 5, "H/M/S", th_format_num)
    ows.write(row_out, 6, "Prevaljeni put (km)", th_format_num)
    ows.write(row_out, 7, "Prosječna brzina (km/h)", th_format_num)
    ows.write(row_out, 8, "Cestarina (HRK)", th_format_num)    
    row_out += 1

    # scan through the original sheet, find where toll'd transactions are
    for rownum in range(1 + header_rownum, worksheet.nrows):
        if 'Cestarina' == worksheet.cell_value(rownum, HAC_Sheet.col_Tip_transakcije.value):
            vr_ul_str = worksheet.cell_value(rownum, HAC_Sheet.col_Vrijeme_ulaska.value)
            vr_iz_str = worksheet.cell_value(rownum, HAC_Sheet.col_Vrijeme_izlaska.value)
            relacija  = worksheet.cell_value(rownum, HAC_Sheet.col_Relacija.value)
            [ od, do ] = relacija.split(' - ')
            toll_hrk = hrk_value(worksheet.cell_value(rownum, HAC_Sheet.col_Isplata_HRK.value))
            
            vr_ul_dt  = hac_date(vr_ul_str)
            vr_iz_dt  = hac_date(vr_iz_str)

            duration = (vr_iz_dt - vr_ul_dt).total_seconds()

            hac_od = HAC_gpsPoints.lookup(od)
            hac_do = HAC_gpsPoints.lookup(do)

            # these are overriden with looked up responses
            
            hac_do_gps = None

            if hac_od is None:
                hac_od_gps = None
                if od not in missing_topo:
                    missing_topo.add(od)
                    logging.warning(f'Naplatna postaja "{od}" nije uvedena u CSV datoteku (check CSV file)')
            else:
                hac_od_gps = hac_od.getPoint('ulaz')
                if hac_od_gps is None:
                    if od not in missing_topo_ul:
                        missing_topo_ul.add(od)
                        logging.warning(f'Naplatnoj postaji "{od}" nije navedena GPS točka \'ulaz\' (check CSV file)')

            if hac_do is None:
                hac_do_gps = None
                if do not in missing_topo:
                    missing_topo.add(od)
                    logging.warning(f'Naplatna postaja "{do}" nije uvedena u CSV datoteku (check CSV file)')
            else:
                hac_do_gps = hac_do.getPoint('izlaz')
                if hac_do_gps is None:
                    if do not in missing_topo_iz:
                        missing_topo_iz.add(do)
                        logging.warning(f'Naplatnoj postaji "{do}" nije navedena GPS točka \'izlaz\' (check CSV file)')


            if hac_od_gps and hac_do_gps:
                dist = tomtom_getDistance(tomtom_url(hac_od_gps, hac_do_gps))
                dist_km = dist/1000.0
                avg_speed_kmh = dist_km/(duration/3600.0)
            else:
                dist = None
                dist_km = None
                avg_speed_kmh = None

            # write row to JSON output, with the following info fields added:
            # duration - seconds, duration - human readable, dist_km, avg_speed_kmh
            json_obj = {
                "od": od,
                "do": do, 
                "od_gps": { "lon": hac_od_gps[0], "lat": hac_od_gps[1]} if hac_od_gps else None,
                "do_gps": { "lon": hac_do_gps[0], "lat": hac_do_gps[1]} if hac_do_gps else None,
                "vr_ulaz":  vr_ul_str,
                "vr_izlaz": vr_iz_str,
                "duration_sec": duration,
                "duration_human": humanize_time(duration),
                "dist_km": (float(format(dist_km, '.1f')) if dist_km is not None else None),
                "avs_kmh": (float(format(avg_speed_kmh, '.1f')) if avg_speed_kmh is not None else None),
                "toll_hrk": toll_hrk
            }
            if DEBUG > 1:
                logging.debug(json.dumps(json_obj))
            json.dump(json_obj, of, sort_keys=False)
            of.write('\n')

            # add a row to Excel sheet output
            ows.write(row_out, 0, od)
            ows.write(row_out, 1, do)
            ows.write(row_out, 2, vr_ul_str)
            ows.write(row_out, 3, vr_iz_str)
            ows.write(row_out, 4, duration)
            ows.write(row_out, 5, json_obj['duration_human'], hms_format)
            if dist_km:
                ows.write(row_out, 6, json_obj['dist_km'], num_format)
                ows.write(row_out, 7, json_obj['avs_kmh'], num_format)
            ows.write(row_out, 8, json_obj['toll_hrk'], hrk_format)
            row_out += 1

    # end for
    of.close()
    owb.close()

    # TODO: izbaciti malo bogatiji summary na kraju, dodati zbirni redak u Excel
    logging.info(f'Zapisano ukupno {row_out} slogova u izlaznu Excel datoteku "{xlsx_out_fn}"')



def parse_args(args):
    """ Parse cmdline args """
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--gps-csv-file", help="GPS entry and exit pins file",
                        default="hac-ulazi-izlazi.csv")
    parser.add_argument("-l", "--log-file", help="log file name to be created",
                        default="hac-xform-{:%Y%m%d}.log")
    parser.add_argument("-x", "--output-xlsx", help="output Excel file to be created",
                        default="hac-xform-{:%Y%m%d}.xlsx")
    parser.add_argument("-j", "--output-json", help="output JSON file to be created",
                        default="hac-xform-{:%Y%m%d}.json")                        
    parser.add_argument("args", nargs='+')
    return parser.parse_args(args)


def logging_init(args):
    """ Initialize logging """
    global DEBUG
    logging.basicConfig(filename=args.log_file.format(datetime.now()),
        level = logging.DEBUG if DEBUG else logging.INFO,
        format = '%(asctime)s %(levelname)s %(message)s')


def process_hac_workbook(wbfile, xlsx_out_fn, json_out_fn):
    workbook = xlrd.open_workbook(wbfile)
    worksheet = workbook.sheet_by_index(0)
    validate_format(worksheet)
    scan_worksheet(worksheet, xlsx_out_fn, json_out_fn)


def main():
    args = parse_args(sys.argv[1:])
    logging_init(args)
    logging.info("HAC Sheet Transformer started, with DEBUG environment variable value set to {}".format(repr(DEBUG)))
    HAC_gpsPoints.loadFromCsvFile(args.gps_csv_file)
    process_hac_workbook(args.args[0], args.output_xlsx, args.output_json)
    logging.info("HAC Sheet Transformer finished")
    return 0

if __name__ == "__main__":
    sys.exit(main())

