#!/usr/bin/python

"""
This is the main entry point for My TA
"""

import os.path as op
import sys
import time
from ...splunktalib import modinput
from ...splunktalib.common import util as utils
from ..common import log as stulog
from . import ta_data_loader as dl
from . import ta_config as tc
from . import ta_checkpoint_manager as cpmgr
from ...splunktalib import orphan_process_monitor as opm

from ...splunktalib import file_monitor as fm
from ..common import load_schema_file as ld
from . import ta_data_client as tdc

utils.remove_http_proxy_env_vars()


def do_scheme(ta_short_name, ta_name, schema_para_list=None,
              single_instance=True):
    """
    Feed splunkd the TA's scheme

    """
    param_str = ""
    builtsin_names = {"name", "index", "sourcetype", "host", "source",
                      "disabled",
                      "interval"}

    schema_para_list = schema_para_list or ()
    for param in schema_para_list:
        if param in builtsin_names:
            continue
        param_str += """<arg name="{param}">
          <title>{param}</title>
          <required_on_create>0</required_on_create>
          <required_on_edit>0</required_on_edit>
        </arg>""".format(param=param)


    print """
    <scheme>
    <title>Splunk Add-on for {ta_short_name}</title>
    <description>Enable data inputs for {ta_name}</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>{}</use_single_instance>
    <endpoint>
      <args>
        <arg name="name">
          <title>{ta_name} Data Input Name</title>
        </arg>
        {param_str}
      </args>
    </endpoint>
    </scheme>
    """.format((str(single_instance)).lower(),ta_short_name=ta_short_name,
               ta_name=ta_name, param_str=param_str)


def _setup_signal_handler(data_loader, ta_short_name):
    """
    Setup signal handlers
    :data_loader: data_loader.DataLoader instance
    """

    def _handle_exit(signum, frame):
        stulog.logger.info("{} receives exit signal".format(ta_short_name))
        if data_loader is not None:
            data_loader.tear_down()

    utils.handle_tear_down_signals(_handle_exit)


def _handle_file_changes(data_loader):
    """
    :reload conf files and exit
    """

    def _handle_refresh(changed_files):
        stulog.logger.info("Detect {} changed, reboot itself".format(
            changed_files))
        data_loader.tear_down()

    return _handle_refresh


def _get_conf_files(settings):
    rest_root = settings.get("meta").get("restRoot")
    configs = settings.get("pages").get("configuration")
    file_list = [rest_root+"_settings.conf"]
    tabs = configs.get("tabs")
    for tab in tabs:
        if tab.get("table"):
            file_list.append(rest_root + "_" + tab.get("name") + ".conf")
    cur_dir = op.dirname(op.dirname(op.dirname(op.dirname(
        op.dirname(op.dirname(op.abspath(
        __file__)))))))
    files = []
    for f in file_list:
        files.append(op.join(cur_dir, "local", f))
    return files


def run(collector_cls, settings, checkpoint_cls=None, config_cls=None,
        log_suffix=None, single_instance=True, cc_json_file=None):
    """
    Main loop. Run this TA forever
    """
    ta_short_name = settings["meta"]["name"].lower()

    # This is for stdout flush
    utils.disable_stdout_buffer()

    # http://bugs.python.org/issue7980
    time.strptime('2016-01-01', '%Y-%m-%d')

    loader = dl.create_data_loader()

    # handle signal
    _setup_signal_handler(loader, ta_short_name)

    # monitor files to reboot
    try:
        monitor = fm.FileMonitor(_handle_file_changes(loader),
                              _get_conf_files(settings))
        loader.add_timer(monitor.check_changes, time.time(), 10)
    except Exception:
        stulog.logger.exception("Fail to add files for monitoring")

    # add orphan process handling, which will check each 1 second
    orphan_checker = opm.OrphanProcessChecker(loader.tear_down)
    loader.add_timer(orphan_checker.check_orphan, time.time(), 1)

    tconfig = tc.create_ta_config(settings, config_cls or tc.TaConfig,
                                  log_suffix, single_instance=single_instance)
    #stulog.set_log_level(tconfig.get_log_level())
    task_configs = tconfig.get_task_configs()

    if not task_configs:
        stulog.logger.debug("No task and exiting...")
        return
    meta_config = tconfig.get_meta_config()
    meta_config["cc_json_file"] = cc_json_file

    if tconfig.is_shc_member():
        # In SHC env, only captain is able to collect data
        stulog.logger.debug("This host is in search head cluster environment , "
                            "will exit.")
        return

    jobs = [tdc.create_data_collector(loader, tconfig, meta_config, task_config,
                                      collector_cls,
            checkpoint_cls=checkpoint_cls or cpmgr.TACheckPointMgr)
            for task_config in task_configs]

    loader.run(jobs)


def validate_config():
    """
    Validate inputs.conf
    """

    _, configs = modinput.get_modinput_configs_from_stdin()
    return 0


def usage():
    """
    Print usage of this binary
    """

    hlp = "%s --scheme|--validate-arguments|-h"
    print >> sys.stderr, hlp % sys.argv[0]
    sys.exit(1)


def main(collector_cls, schema_file_path, log_suffix="modinput",
         checkpoint_cls=None, configer_cls=None,
         cc_json_file=None, schema_para_list=None,
         single_instance=True):
    """
    Main entry point
    """
    assert collector_cls, "ucc modinput collector is None."
    assert schema_file_path, "ucc modinput schema file is None"

    stulog.reset_logger(log_suffix)
    settings = ld(schema_file_path)
    ta_short_name = settings["meta"]["name"].lower()
    ta_desc = settings["meta"]["displayName"].lower()

    args = sys.argv
    if len(args) > 1:
        if args[1] == "--scheme":
            do_scheme(ta_short_name, ta_desc, schema_para_list,
                      single_instance)
        elif args[1] == "--validate-arguments":
            sys.exit(validate_config())
        elif args[1] in ("-h", "--h", "--help"):
            usage()
        else:
            usage()
    else:
        stulog.logger.info("Start {} task".format(ta_short_name))
        try:
            run(collector_cls, settings, checkpoint_cls=checkpoint_cls,
                config_cls=configer_cls, log_suffix=log_suffix,
                single_instance=single_instance, cc_json_file=cc_json_file)
        except Exception as e:
            stulog.logger.exception(
                "{} task encounter exception".format(ta_short_name))
        stulog.logger.info("End {} task".format(ta_short_name))
    sys.exit(0)
