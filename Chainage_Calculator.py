# Calculate chainage
# centerline must be split in section
# third field have to be Section
# centerline have to be inside .gdb
# Avoid feature names Cntr_Sec and KP_Sec


import arcpy
import os
import json
import time

arcpy.env.overwriteOutput = 1


def calculate(cntr, path):
    arcpy.env.workspace = path
    fields = ['SHAPE@LENGTH']
    for i in arcpy.ListFields(cntr):
        fields.append(i.name)
    print(fields)
    with arcpy.da.SearchCursor(cntr, fields) as cursor:
        #fix sort geometry
        print("checking and fixing orientation error...")
        sortReversed(cntr)
        for i in cursor:
            where_clause = '"{}" = \'{}\''.format(fields[3], i[3])
            section_length = round(i[0], 1)
            current_cntr = arcpy.Select_analysis(cntr, os.path.join(path, "Cntr_Sec_" + i[3]), where_clause)
            current_kp = arcpy.management.GeneratePointsAlongLines(current_cntr, os.path.join(path, "KP_Sec_" + i[3]),
                                                                   "DISTANCE", "10 Meters", None, "END_POINTS")
            arcpy.AddField_management(current_kp, "KP_number", "FLOAT", None)
            arcpy.AddField_management(current_kp, "KP_txt", "TEXT", None, None, 20)
            lastID = ''
            with arcpy.da.SearchCursor(current_kp, ["OID@"]) as Cursor2:
                for j in Cursor2:
                    lastID = j[0]
            # calculate KP
            calc_int(current_kp, ["OID@", "KP_number"], section_length, lastID)
            # convert kp to txt
            kp2txt(current_kp, ["OID@", "KP_number", "KP_txt"], i[3], section_length, lastID)
            print(f"finished Section: {i[3]}")
    # Merge all together
    cntr_total = []
    kp_total = []
    for i in arcpy.ListFeatureClasses():
        if i[:6] == "KP_Sec":
            kp_total.append(i)
        elif i[:8] == "Cntr_Sec":
            cntr_total.append(i)
    arcpy.Merge_management(kp_total, "KP_Total")
    # deleting files
    for i in cntr_total:
        arcpy.Delete_management(i)
    for j in kp_total:
        arcpy.Delete_management(j)

#case when flow start in south and ends in noth
def sortReversed(cntr):
    coordinates = []
    with arcpy.da.UpdateCursor(cntr, ["SHAPE@JSON"]) as cursor:
        for i in cursor:
            str_json = ""
            coordinates = []
            json_object = json.loads(i[0])
            first_y = json_object["paths"][0][0][1]
            last_y = json_object["paths"][0][-1][1]

            if first_y > last_y:
                coordinates = json_object["paths"][0]
                coordinates.reverse()
                json_object["paths"] = [coordinates]
                str_json = '{}'.format(json_object)
                str_json = str_json.replace('None', 'null')
                str_json = str_json.replace('True', 'true')
                str_json = str_json.replace('False', 'false')
                str_json = str_json.replace(' ', '')
                i = [str_json]
                time.sleep(1)
                print("Fixed - ")
                print(i)
                cursor.updateRow(i)




def calc_int(chainage, field, length, lastID):
    start_kp = 0
    with arcpy.da.UpdateCursor(chainage, field) as cursor:
        for row in cursor:
            if row[0] == lastID:
                row[1] = length
                cursor.updateRow(row)
                break
            row[1] = start_kp
            start_kp += 10
            cursor.updateRow(row)


def kp2txt(chainage, field, section, section_length, lastID):
    with arcpy.da.UpdateCursor(chainage, field) as cursor:
        for row in cursor:
            temp = str(int(row[1]))
            if row[1] == 0:
                row[2] = f"{section}0+000"
            elif len(temp) == 2:
                row[2] = f"{section}0+0" + temp
            elif len(temp) == 3:
                row[2] = "{0}0+".format(section) + temp
            elif len(temp) == 4:
                row[2] = section + temp[:1] + "+" + temp[1:]
            else:
                row[2] = f"{section}{temp[:2]}+" + temp[2:]

            if row[0] == lastID:
                if section_length < 10000:
                    row[2] = section + str(section_length)[:1] + "+" + str(section_length)[1:]
                else:
                    row[2] = section + str(section_length)[:2] + "+" + str(section_length)[2:]
            cursor.updateRow(row)


if __name__ == '__main__':
    centreline = r"C:\Temp\test\gdb.gdb\Cntr"
    arcpy.AddMessage(centreline)
    arcpy.DefineProjection_management(centreline,
                                      'PROJCS["British_National_Grid",GEOGCS["GCS_OSGB_1936",DATUM["D_OSGB_1936",SPHEROID["Airy_1830",6377563.396,299.3249646]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",400000.0],PARAMETER["False_Northing",-100000.0],PARAMETER["Central_Meridian",-2.0],PARAMETER["Scale_Factor",0.9996012717],PARAMETER["Latitude_Of_Origin",49.0],UNIT["Meter",1.0]]')
    workspace = os.path.split(centreline)[0]
    calculate(centreline, workspace)