import os


def use_latest_cc_build(cclib_path,sample_ta_path):
    ta_dir = os.listdir(sample_ta_path)
    for item in ta_dir:
        item_abs_path = os.path.join(sample_ta_path,item)
        if os.path.isdir(item_abs_path):
             print"In folder ", item
             local_cclib_path = os.path.join(item_abs_path,"bin",item.lower(),"cloudconnectlib")
             local_cc_parent_path = os.path.join(item_abs_path,"bin",item.lower())
             if os.path.exists(local_cclib_path):
                 remove_cmd_string = "rm -rf {}".format(local_cclib_path)
                 os.system(remove_cmd_string)
                 print "Remove Local cloudConnect Lib"

             cp_cmd_string = "cp -r {} {}".format(cclib_path,local_cc_parent_path)
             os.system(cp_cmd_string)
             print "Copy latest CloudConnectLib from Desktop"

def use_latestucc_build(ucclib_path,sample_ta_path):



    ta_dir = os.listdir(sample_ta_path)
    for item in ta_dir:
        item_abs_path = os.path.join(sample_ta_path,item)
        if os.path.isdir(item_abs_path):
             print"In folder ", item
             local_ucclib_path = os.path.join(item_abs_path,"bin",item.lower(),"splunktaucclib")
             local_ucc_parent_path = os.path.join(item_abs_path,"bin",item.lower())
             if os.path.exists(local_ucclib_path):
                 remove_cmd_string = "rm -rf {}".format(local_ucclib_path)
                 os.system(remove_cmd_string)
                 print "Remove Local UCC Lib"

             cp_cmd_string = "cp -r {} {}".format(ucclib_path,local_ucc_parent_path)
             os.system(cp_cmd_string)
             print "Copy latest UCCLib from package"

cclib_path = "/Users/cloris/Desktop/cloudconnectlib"
ucclib_path = "/Users/cloris/ta-ui-framework/UCC-REST-lib/splunktaucclib"
sample_ta_path = "/Users/cloris/cloud-connect-engine/examples/1.0/mytest"
use_latest_cc_build(cclib_path,sample_ta_path)
use_latestucc_build(cclib_path,sample_ta_path)