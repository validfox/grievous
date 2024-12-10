#!/usr/bin/env python3

#
# Author: xeroncn+validfox.grievous@gmail.com
# Date: 2024.12.10
# Licensed under the MIT license. See LICENSE file in the project root for details.
#

#import sys, os, re, glob, stat, shutil, collections, random, datetime, time, threading, signal
import sys, os, datetime, shutil, re, collections, threading, random, glob, time, signal

sys.dont_write_bytecode = True

time_label = datetime.datetime.now().strftime('%m%d%H%M%S')
start_time = datetime.datetime.now()
end_time = datetime.datetime.now() #update by the end of the script

sim_types_list = ['rtl', 'gls', 'fpga', 'cosim', 'fault']
wave_types_list = ['shm', 'fsdb', 'vcd', 'vpd']
simulators_list = ['nc', 'vcs']

cmd_line_args_dict = {} #store the information on command line
cfg_file_items_dict = {} #store the information in configuration file or files
help_doc_dict = collections.OrderedDict() #store the description of each arguments, including custom switches
custom_switch_on_cmd_line_dict = {} #unknown arguments on command line are treated as custom switches
custom_switch_in_cfg_file_dict = {} #custom swithces which are defined in configuration files
case_list_in_regression = {} #store all tests in regression
                            #{test0: [{switch:'', repeat:''}, {switch:'', repeat:''}],
                            # test1: [{switch:'', repeat:''}, {switch:'', repeat:''}]}
total_runs_in_regression = 0
running_runs_in_regression = 0
error_runs_in_regression = 0
warn_runs_in_regression = 0
pass_runs_in_regression = 0
generated_folders_info_dict = {} #the names of all generated folders go here
                                #{sim folder0: {seed:'', parent:'', script:'', shellcmd:'', logs:[], result:'', done:True/False},
                                # sim folder1: {seed:'', parent:'', script:'', shellcmd:'', logs:[], result:'', done:True/False}}

sim_base_dir = '' #simulation folder or regression folder

thread_list = []
pool_sema = ''

global_info_msg = []

debug_enable_flag = False
single_simulation_flag = True #single simulation by default
regression_flag = False
block_simulation_flag = False
top_simulation_flag = True
localdv_flag = False

env_usr = os.getenv('USER', 'undefine')
env_hostname = os.getenv('HOSTNAME', 'undefine')
env_prj_name = os.getenv('PRJ_NAME', 'undefine')
env_prj_root = os.getenv('PRJ_ROOT', 'undefine')
env_design_root = os.getenv('DESIGN_ROOT', 'undefine')
env_dv_root = os.getenv('DV_ROOT', 'undefine')
env_sim_root = os.getenv('SIM_ROOT', 'undefine')

global_defines = []

period_print_msg_interval = 14
ctrl_c_times = 0
pre_ctrl_c_time = datetime.datetime.now()
jobs_were_killed_by_two_ctrl_c = False

def f_parse_cmd_line(arg_list):
    print(arg_list)
    global cmd_line_args_dict
    global custom_switch_on_cmd_line_dict
    global debug_enable_flag
    global single_simulation_flag
    global regression_flag
    global block_simulation_flag
    global top_simulation_flag
    global localdv_flag
    global global_defines
    _all_args = iter(range(0, len(arg_list)))
    for _i in _all_args:
        _curr = str(arg_list[_i])
        _next = '' if (_i>=len(arg_list)-1) else str(arg_list[_i+1])
        if _curr in {'--debug'}:
            cmd_line_args_dict['debug'] = True
            debug_enable_flag = True
        elif _curr in {'-h', '-help'}:
            cmd_line_args_dict['help'] = True
            f_print_help()
        elif _curr in {'-t', '-test'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('testname is not specified')
            if not _next in cmd_line_args_dict['test']: cmd_line_args_dict['test'].append(_next)
            next(_all_args)
        elif _curr in {'-r', '-regr'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('regression list is not specified')
            if not _next in cmd_line_args_dict['regr']: cmd_line_args_dict['regr'].append(_next)
            next(_all_args)
        elif _curr in {'-g', '-group'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('regression group name is not specified')
            if not _next in cmd_line_args_dict['regr_group']: cmd_line_args_dict['regr_group'].append(_next)
            next(_all_args)
        elif _curr in {'-uvm'}:
            cmd_line_args_dict['uvm'] = True
        elif _curr in {'-nouvm', '--uvm'}:
            cmd_line_args_dict['uvm'] = False
        elif _curr in {'-c', '-clean'}:
            cmd_line_args_dict['clean'] = True
        elif _curr in {'-s', '-seed'}:
            cmd_line_args_dict['seed'] = _next
            next(_all_args)
        elif _curr in {'-w', '-wave'}:
            cmd_line_args_dict['wave'] = True
            if _next and not _next[0] in {'-', '+'}:
                cmd_line_args_dict['wave_type'] = _next.lower()
                next(_all_args)
        elif _curr in {'-wall'}:
            cmd_line_args_dict['wall'] = True
            if _next and not _next[0] in {'-', '+'}:
                cmd_line_args_dict['wave_type'] = _next.lower()
                next(_all_args)
        elif _curr in {'-atm'}:
            cmd_line_args_dict['automsg'] = True
        elif _curr in {'-noatm', '--atm'}:
            cmd_line_args_dict['automsg'] = False
        elif _curr in {'-input'}: #for ncsim
            if not _next or _next[0] in {'-', '+'}: sys.exit('input tcl file is not specified')
            cmd_line_args_dict['tcl_files'].append(_next)
            next(_all_args)
        elif _curr in {'-b', '-block'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('block name is not specified')
            cmd_line_args_dict['block'] = _next
            block_simulation_flag = True
            top_simulation_flag = False
            next(_all_args)
        elif re.match(r'^-dv\d*$', _curr): #-dv, -dv0, -dv1, ...
            cmd_line_args_dict['dv_folder'] = _curr[1:]
        elif re.match(r'^-localdv\d*$', _curr): #-localdv, -localdv0, -localdv1, ...
            cmd_line_args_dict['dv_folder'] = _curr[1:]
            localdv_flag = True
        elif _curr in {'-rtl'}:
            cmd_line_args_dict['sim_type'] = 'rtl'
        elif _curr in {'-gate', '-gls'}:
            cmd_line_args_dict['sim_type'] = 'gls'
        elif _curr in {'-fpga'}:
            cmd_line_args_dict['sim_type'] = 'fpga'
        #elif _curr in {'-cosim'}:
        #    cmd_line_args_dict['sim_type'] = 'cosim'
        #elif _curr in {'-fault', '-fusa'}:
        #    cmd_line_args_dict['sim_type'] = 'fault'
        elif _curr in {'-tfile'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('tfile is not specified')
            cmd_line_args_dict['tfiles'].append(_next)
            next(_all_args)
        elif _curr in {'-lsf'}:
            cmd_line_args_dict['lsf'] = True
        elif _curr in {'-nolsf', '--lsf'}:
            cmd_line_args_dict['lsf'] = False
        elif _curr in {'-interactivelsf'}:
            cmd_line_args_dict['lsf'] = True
            cmd_line_args_dict['interactivelsf'] = True
        elif _curr in {'-nointeractivelsf', '--interactivelsf'}:
            cmd_line_args_dict['lsf'] = True
            cmd_line_args_dict['interactivelsf'] = False
        elif _curr in {'-jname'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('lsf job group name is not specified')
            cmd_line_args_dict['lsf_job_group_name'] = _next
            next(_all_args)
        elif _curr in {'-regrchild'}: #in regression, some item are treated as single sim, in order to call $0 recurively
            cmd_line_args_dict['single_in_regr'] = True
        elif _curr in {'-rcn', '-compile_repeat_number'}: #repeat number in compile stage after failure
            if not _next or _next[0] in {'-', '+'}: sys.exit('compile repeat number is not specified')
            cmd_line_args_dict['compile_repeat_number'] = _next
            next(_all_args)
        elif _curr in {'-sim_root'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('sim_root is not specified')
            cmd_line_args_dict['sim_root'] = _next
            next(_all_args)
        elif _curr in {'-d', '-dir', '-sim_folder'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('simulation folder is not specified')
            cmd_line_args_dict['sim_folder'] = _next
            next(_all_args)
        elif _curr in {'-repeat'}:
            cmd_line_args_dict['repeat_times'] = int(_next) if int(_next)>0 else 1
            next(_all_args)
        elif _curr in {'-append'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('append folder name is not specified')
            cmd_line_args_dict['append_dir_name'] += '_'+_next
            next(_all_args)
        elif _curr in {'-setup', '-force_simsetup', '-force_setup'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('configuration file is not specified')
            cmd_line_args_dict['sim_setup'] = _next
            next(_all_args)
        elif _curr in {'-max'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('parallel run number is not specified')
            cmd_line_args_dict['max_run_in_parallel'] = int(_next) if int(_next)>0 else 1
            next(_all_args)
        elif _curr in {'-qc', '-quit_count'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('quit number is not specified')
            cmd_line_args_dict['max_quit_count'] = int(_next) if int(_next)>0 else '1'
            next(_all_args)
        elif _curr in {'-m', '-host'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('running host is not specified')
            cmd_line_args_dict['lsf_hosts'].append(_next)
            next(_all_args)
        elif _curr in {'-inf'}:
            cmd_line_args_dict['infinite_run'] = True #'bsub -c 1200' means run 20 hours at most TODO: not implemented yet
        elif _curr in {'-ext_lsf_opt'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('extra LSF argument is not specified')
            cmd_line_args_dict['extra_lsf_options'].append(_next)
            next(_all_args)
        elif _curr in {'-ext_comp_opt'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('extra compile argument is not specified')
            cmd_line_args_dict['extra_comp_options'].append(_next)
            next(_all_args)
        elif _curr in {'-ext_sim_opt'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('extra simulate argument is not specified')
            cmd_line_args_dict['extra_sim_options'].append(_next)
            next(_all_args)
        elif _curr in {'-ext_opt'}: #extra options for both compile and simulate stages
            if not _next or _next[0] in {'-', '+'}: sys.exit('extra compile/simulate argument is not specified')
            cmd_line_args_dict['extra_comp_options'].append(_next)
            cmd_line_args_dict['extra_sim_options'].append(_next)
            next(_all_args)
        elif _curr in {'-ext_dbg_opt'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('extra waveform viewer argument is not specified')
            cmd_line_args_dict['extra_dbg_options'].append(_next)
            next(_all_args)
        elif _curr in {'-co', '-compile_only'}:
            cmd_line_args_dict['compile_only'] = True
        elif _curr in {'-gs', '-gen_script', '-gen_scripts', '-gen_scripts_only'}:
            cmd_line_args_dict['gen_scripts_only'] = True
        elif _curr in {'-cov'}:
            cmd_line_args_dict['cov_cmd_line'] = True
            cmd_line_args_dict['cov_enable'] = True
        elif _curr in {'-cm', '-cov_merge'}:
            cmd_line_args_dict['cov_merge'] = True
        elif _curr in {'-nocov'}:
            cmd_line_args_dict['nocov_cmd_line'] = True
        elif _curr in {'-refine'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('refine file of coverage is not specified')
            cmd_line_args_dict['cov_refine_files'].append(_next)
            next(_all_args)
        elif _curr in {'-dailyfoldername'}: #name only
            if not _next or _next[0] in {'-', '+'}: sys.exit('-dailyfolder is not specified')
            cmd_line_args_dict['daily_folder'] = _next
            next(_all_args)
        elif _curr in {'-gui'}:
            cmd_line_args_dict['sim_on_gui'] = True
        elif _curr in {'-nc'}:
            cmd_line_args_dict['simulator'] = 'nc'
        elif _curr in {'-vcs'}:
            cmd_line_args_dict['simulator'] = 'vcs'
        elif _curr in {'-simtmp'}:
            if not _next or _next[0] in {'-', '+'}: sys.exit('sim_tmp of nc is not specified')
            cmd_line_args_dict['sim_tmp'] = _next
            next(_all_args)
        elif _curr in {'-[', '-]'}: #cmd line args pass from upper level, not happened to script
            pass
        elif _curr.startswith('+'):
            cmd_line_args_dict['plus_args'].append(_curr)
        elif _curr.startswith('--'):
            cmd_line_args_dict['disable_custom_switch'].append(_curr.replace('--', ''))
        elif _curr.startswith('-'):
            if (not _next) or (_next[0] in {'-', '+'}):
                cmd_line_args_dict['enable_custom_switch_valueless'][_curr.replace('-', '')] = True
            else:
                cmd_line_args_dict['enable_custom_switch_valuable'][_curr.replace('-', '')] = _next
                next(_all_args)
        elif _curr != sys.argv[0]:
            cmd_line_args_dict['unknown'].append(_curr)
    #post process of input args
    if len(cmd_line_args_dict['test'])>1 or len(cmd_line_args_dict['regr'])>0 or cmd_line_args_dict['repeat_times']>1:
        single_simulation_flag = False
        regression_flag = True
        if not cmd_line_args_dict['regr']: cmd_line_args_dict['regr_group']= ['default']
        cmd_line_args_dict['regr_group'].sort()
    if (not localdv_flag) and (not cmd_line_args_dict['test'] and not cmd_line_args_dict['regr']):
        sys.exit('No test and regression list is specified in command line.')
    if regression_flag: cmd_line_args_dict['interactivelsf'] = False #for regression, interactive lsf is disabled
    if cmd_line_args_dict['cov_cmd_line'] and cmd_line_args_dict['nocov_cmd_line']: #-nocov has higher priority
        cmd_line_args_dict['cov_enable'] = False
        cmd_line_args_dict['cov_merge'] = False
    if not cmd_line_args_dict['cov_enable']: cmd_line_args_dict['cov_merge'] = False
    for _c, _v in cmd_line_args_dict['enable_custom_switch_valueless'].items():
        custom_switch_on_cmd_line_dict[_c] = '_valueless'
    for _c, _v in cmd_line_args_dict['enable_custom_switch_valuable'].items():
        if _v.lower() in {'_valueless', '_disable'}: sys.exit('\"-'+_c+' '+_v+'\" is not legal.')
        custom_switch_on_cmd_line_dict[_c] = _v
    for _c in cmd_line_args_dict['disable_custom_switch']:
        custom_switch_on_cmd_line_dict[_c] = '_disable'
    #post process
    global_defines.append('_CMD_LINE_=\\\"'+(' '.join(arg_list)).replace('-[','').replace('-]','').replace('\"','\'').replace(' ','\\ ')+'\\\"') #FIXME
    global_defines.append('_SIM_ONLY_')
    global_defines.append('_USER_=\\\"'+env_usr+'\\\"')
    global_defines.append('_HOSTNAME_=\\\"'+env_hostname+'\\\"')
    global_defines.append('_PRJ_NAME_=\\\"'+env_prj_name+'\\\"')
    global_defines.append('_PRJ_ROOT_=\\\"'+env_prj_root+'\\\"')
    global_defines.append('_DESIGN_ROOT_=\\\"'+env_design_root+'\\\"')
    global_defines.append('_DV_ROOT_=\\\"'+env_dv_root+'\\\"')
    global_defines.append('_SIM_ROOT_=\\\"'+env_sim_root+'\\\"')
    if cmd_line_args_dict['uvm']:
        global_defines.append('_UVM_EN_')
    if single_simulation_flag:
        global_defines.append('_SINGLE_SIM_')
    if regression_flag:
        global_defines.append('_REGR_')
    if block_simulation_flag:
        global_defines.append('_BLK_DV_')
    if top_simulation_flag:
        global_defines.append('_TOP_DV_')
    if cmd_line_args_dict['lsf']:
        global_defines.append('_LSF_')
    if cmd_line_args_dict['interactivelsf']:
        global_defines.append('_INTERACTIVE_LSF_')
    global_defines.append('_SIMULATOR_=\\\"'+cmd_line_args_dict['simulator'].upper()+'\\\"')
    global_defines.append('_SIM_TYPE_=\\\"'+cmd_line_args_dict['sim_type'].upper()+'\\\"')
    if cmd_line_args_dict['wave']:
        global_defines.append('_DUMP_WAVE_=\\\"'+cmd_line_args_dict['wave_type'].upper()+'\\\"')
    #post process
    cmd_line_args_dict['next_level_args'].append('-uvm' if cmd_line_args_dict['uvm'] else '-nouvm')
    #cmd_line_args_dict['next_level_args'].append('-s '+cmd_line_args_dict['seed'])
    if cmd_line_args_dict['wall']: cmd_line_args_dict['next_level_args'].append('-wall '+cmd_line_args_dict['wave_type'])
    if cmd_line_args_dict['wave']: cmd_line_args_dict['next_level_args'].append('-w '+cmd_line_args_dict['wave_type'])
    cmd_line_args_dict['next_level_args'].append('-atm' if cmd_line_args_dict['automsg'] else '-noatm')
    for _tcl_file in cmd_line_args_dict['tcl_files']: cmd_line_args_dict['next_level_args'].append('-input '+_tcl_file)
    if cmd_line_args_dict['block']: cmd_line_args_dict['next_level_args'].append('-b '+cmd_line_args_dict['block'])
    cmd_line_args_dict['next_level_args'].append('-'+cmd_line_args_dict['sim_type'])
    for _tfile in cmd_line_args_dict['tfiles']: cmd_line_args_dict['next_level_args'].append('-tfile '+_tfile)
    cmd_line_args_dict['next_level_args'].append('-rcn '+cmd_line_args_dict['compile_repeat_number'])
    cmd_line_args_dict['next_level_args'].append('-sim_root '+cmd_line_args_dict['sim_root'])
    if cmd_line_args_dict['sim_setup']: cmd_line_args_dict['next_level_args'].append('-setup '+cmd_line_args_dict['sim_setup'])
    for _eco in cmd_line_args_dict['extra_comp_options']: cmd_line_args_dict['next_level_args'].append('-ext_comp_opt '+_eco)
    for _eso in cmd_line_args_dict['extra_sim_options']: cmd_line_args_dict['next_level_args'].append('-ext_sim_opt '+_eso)
    for _edo in cmd_line_args_dict['extra_dbg_options']: cmd_line_args_dict['next_level_args'].append('-ext_dbg_opt '+_edo)
    cmd_line_args_dict['next_level_args'].append('-cov' if cmd_line_args_dict['cov_enable'] else '-nocov')
    cmd_line_args_dict['next_level_args'].append('-'+cmd_line_args_dict['simulator'])
    if cmd_line_args_dict['sim_tmp']: cmd_line_args_dict['next_level_args'].append('-simtmp '+cmd_line_args_dict['sim_tmp'])
    for _pa in cmd_line_args_dict['plus_args']: cmd_line_args_dict['next_level_args'].append(_pa)
    for _dcs in cmd_line_args_dict['disable_custom_switch']: cmd_line_args_dict['next_level_args'].append('--'+_dcs)
    for _ecsvless in cmd_line_args_dict['enable_custom_switch_valueless']: cmd_line_args_dict['next_level_args'].append('-'+_ecsvless)
    for _ecsvable, _value in cmd_line_args_dict['enable_custom_switch_valuable'].items(): cmd_line_args_dict['next_level_args'].append('-'+_ecsvable+' '+_value)
    for _unkn in cmd_line_args_dict['unknown']: cmd_line_args_dict['next_level_args'].append(_unkn)

def f_init_dicts():
    global cmd_line_args_dict #############################
    cmd_line_args_dict['debug'] = False
    cmd_line_args_dict['help'] = False
    cmd_line_args_dict['test'] = []
    cmd_line_args_dict['regr'] = []
    cmd_line_args_dict['regr_group'] = []
    cmd_line_args_dict['uvm'] = True
    cmd_line_args_dict['clean'] = False
    cmd_line_args_dict['seed'] = str(random.randint(1,2147483647)) #min:1, max:0x7FFFFFFF #cannot larger than 0x7FFFFFFF or else a negtive seed is got
    cmd_line_args_dict['wave'] = False
    cmd_line_args_dict['wall'] = False
    cmd_line_args_dict['wave_type'] = wave_types_list[1] #wave_types_list = ['shm', 'fsdb', 'vcd', 'vpd']
    cmd_line_args_dict['automsg'] = True
    cmd_line_args_dict['tcl_files'] = []
    cmd_line_args_dict['block'] = ''
    cmd_line_args_dict['dv_folder'] = 'dv'
    cmd_line_args_dict['sim_type'] = sim_types_list[0] #sim_types_list = ['rtl', 'gls', 'fpga', 'cosim', 'fault']
    cmd_line_args_dict['tfiles'] = []
    cmd_line_args_dict['lsf'] = False #True
    cmd_line_args_dict['interactivelsf'] = True #not used when regression
    cmd_line_args_dict['lsf_job_group_name'] = env_usr+time_label
    cmd_line_args_dict['single_in_regr'] = False
    cmd_line_args_dict['compile_repeat_number'] = '3'
    cmd_line_args_dict['sim_root'] = env_sim_root #such like /nobackup/${USER}/${PRJ_NAME}
    cmd_line_args_dict['sim_folder'] = ''
    cmd_line_args_dict['repeat_times'] = 1
    cmd_line_args_dict['append_dir_name'] = '' #note: if -d is used with script, nothing will append to sim_folder
    cmd_line_args_dict['sim_setup'] = 'sim.setup'
    cmd_line_args_dict['max_run_in_parallel'] = 20
    cmd_line_args_dict['max_quit_count'] = -1
    cmd_line_args_dict['lsf_hosts'] = []
    cmd_line_args_dict['infinite_run'] = False #maximum wall time of a lsf job is not set if infinite_run is True
    cmd_line_args_dict['extra_lsf_options'] = []
    cmd_line_args_dict['extra_comp_options'] = []
    cmd_line_args_dict['extra_sim_options'] = []
    cmd_line_args_dict['extra_dbg_options'] = []
    cmd_line_args_dict['compile_only'] = False
    cmd_line_args_dict['gen_scripts_only'] = False
    cmd_line_args_dict['cov_enable'] = False
    cmd_line_args_dict['cov_merge'] = False
    cmd_line_args_dict['cov_cmd_line'] = False
    cmd_line_args_dict['nocov_cmd_line'] = False
    cmd_line_args_dict['cov_refine_files'] = []
    cmd_line_args_dict['daily_folder'] = '' #for daily regression
    cmd_line_args_dict['sim_on_gui'] = False
    cmd_line_args_dict['simulator'] = simulators_list[1] #simulators_list = ['nc', 'vcs']
    cmd_line_args_dict['sim_tmp'] = '' #for nc only, to specify a folder to store tmp files
    cmd_line_args_dict['plus_args'] = []
    cmd_line_args_dict['enable_custom_switch_valueless'] = {}
    cmd_line_args_dict['enable_custom_switch_valuable'] = {}
    cmd_line_args_dict['disable_custom_switch'] = []
    cmd_line_args_dict['unknown'] = []
    cmd_line_args_dict['next_level_args'] = ['-regrchild', '-gs'] #some args should be passed to next level of simulation when the script calls itself, used to create folder and run scirpts
    global cfg_file_items_dict #############################
    cfg_file_items_dict['path_of_cfg_files'] = []
    cfg_file_items_dict['custom_switch'] = []
    cfg_file_items_dict['design_top'] = ''
    cfg_file_items_dict['tb_top'] = ''
    cfg_file_items_dict['inc_dir'] = []
    cfg_file_items_dict['design_files'] = []
    cfg_file_items_dict['dv_files'] = []
    cfg_file_items_dict['lib_files'] = []
    cfg_file_items_dict['model_files'] = []
    cfg_file_items_dict['time_scale'] = '1ns/1fs'
    cfg_file_items_dict['uvm_timeout'] = '10000000000' #10s
    cfg_file_items_dict['max_quit_count'] = -1
    cfg_file_items_dict['tcl_files'] = []
    cfg_file_items_dict['tfiles'] = []
    cfg_file_items_dict['bsub_opt'] = []
    cfg_file_items_dict['ext_opt'] = []
    cfg_file_items_dict['ext_comp_opt'] = []
    cfg_file_items_dict['ext_sim_opt'] = []
    cfg_file_items_dict['ext_dbg_opt'] = []
    cfg_file_items_dict['pre_comp_cmd'] = []
    cfg_file_items_dict['post_comp_cmd'] = []
    cfg_file_items_dict['pre_sim_cmd'] = []
    cfg_file_items_dict['post_sim_cmd'] = []
    cfg_file_items_dict['cov_type'] = []
    cfg_file_items_dict['cov_files'] = []
    cfg_file_items_dict['cov_dut'] = []
    cfg_file_items_dict['cov_refine_files'] = []
    cfg_file_items_dict['warn_str'] = ['UVM_WARNING', '*W', 'Warning!'] #TODO: default warn list? UVM_WARNING? *W?
    cfg_file_items_dict['ignore_warn_str'] = []
    cfg_file_items_dict['err_str'] = ['UVM_ERROR', 'UVM_FATAL', '*E', '*SE', '*F', 'Syntax error', 'Error-', 'Error: '] #TODO: default error list? such as UVM_ERROR? UVM_FATAL? *E? *F?
    cfg_file_items_dict['ignore_err_str'] = []
    cfg_file_items_dict['other_sim_log_files'] = []
    cfg_file_items_dict['blk_root'] = ''
    cfg_file_items_dict['blk_design_root'] = ''
    cfg_file_items_dict['blk_dv_root'] = ''

def f_help_doc():
    global help_doc_dict
    help_doc_dict['-h, -help'] = 'print help'
    help_doc_dict['-t, -test'] = 'specify uvm_test name of testcase, multiple -t are acceptable'
    help_doc_dict['-r, -regr'] = 'specify file name of regression list, multiple -r are acceptable'
    help_doc_dict['-g, -group'] = 'specify group in regression list, multiple -g are acceptable'
    #TBA

def f_print_help():
    print('------Help Docs------\n')
    for _i in help_doc_dict.keys():
        print(_i+': '+help_doc_dict[_i]+'\n')

def f_parse_config_file(input_cfg_file):
    global global_info_msg
    global cfg_file_items_dict
    global custom_switch_in_cfg_file_dict
    global global_defines
    if os.path.exists(input_cfg_file):
        _path_of_cfg_file = input_cfg_file
    elif cmd_line_args_dict['block']:
        _path_of_cfg_file = f_find_file(env_prj_root, cmd_line_args_dict['block']+'/'+cmd_line_args_dict['dv_folder']+'/'+input_cfg_file)
    else:
        _path_of_cfg_file = f_find_file(env_prj_root, cmd_line_args_dict['dv_folder']+'/'+input_cfg_file, env_prj_root+'/'+cmd_line_args_dict['dv_folder'])
    _path_of_cfg_file = os.path.expandvars(_path_of_cfg_file)
    print(_path_of_cfg_file)
    global_info_msg.append(_path_of_cfg_file)
    cfg_file_items_dict['path_of_cfg_files'].append(_path_of_cfg_file)
    with open(_path_of_cfg_file, 'r') as f:
        for _line in f:
            _line = str(_line).replace('\n', '').replace('\t', '').strip()
            if len(_line) == 0: continue
            if (_line[0].isalnum() or _line[0] == '!') and ':' in _line:
                _key, _value = _line.split(':', 1)
                _key = _key.strip()
                _value = _value.strip()
                if len(_key)==0 or len(_value)==0: continue
                if cmd_line_args_dict['debug']: print(_key+':'+_value)
                _sub_key_list = _key.split('_')
                _main_key = ''
                for _sk in _sub_key_list:
                    if _sk[0]=='!' and _sk[1:].islower(): #below lines has priorities
                        if _sk[1:] not in list(custom_switch_in_cfg_file_dict.keys())+sim_types_list+wave_types_list+simulators_list: sys.exit(_sk[1:]+' not defined, or used before declared')
                        if _sk[1:] in custom_switch_on_cmd_line_dict.keys():
                            if custom_switch_on_cmd_line_dict[_sk[1:]] != '_disable': break #if custom switch is not disabled in cmd line by '--'
                        elif _sk[1:] in custom_switch_in_cfg_file_dict.keys():
                            if custom_switch_in_cfg_file_dict[_sk[1:]][1]: break #default:ON
                        if _sk[1:] in sim_types_list:
                            if _sk[1:] == cmd_line_args_dict['sim_type']: break
                        if _sk[1:] in wave_types_list:
                            if _sk[1:] == cmd_line_args_dict['wave_type']: break
                        if _sk[1:] in simulators_list:
                            if _sk[1:] == cmd_line_args_dict['simulator']: break
                        if _sk[1:] == 'singlesim' and single_simulation_flag: break
                        if _sk[1:] == 'regr' and regression_flag: break
                        if _sk[1:] == 'dumpwave' and (cmd_line_args_dict['wave'] or cmd_line_args_dict['wall']): break
                    elif _sk.islower(): #below lines has priorities
                        if _sk not in list(custom_switch_in_cfg_file_dict.keys())+sim_types_list+wave_types_list+simulators_list: sys.exit(_sk+' not defined, or used before declared')
                        if _sk in custom_switch_on_cmd_line_dict.keys():
                            if custom_switch_on_cmd_line_dict[_sk] == '_disable': break #if custom switch is disabled in cmd line by '--'
                        elif _sk in custom_switch_in_cfg_file_dict.keys():
                            if not custom_switch_in_cfg_file_dict[_sk][1]: break #default:OFF
                        if _sk in sim_types_list:
                            if _sk != cmd_line_args_dict['sim_type']: break
                        if _sk in wave_types_list:
                            if _sk != cmd_line_args_dict['wave_type']: break
                        if _sk in simulators_list:
                            if _sk != cmd_line_args_dict['simulator']: break
                        if _sk == 'singlesim' and not single_simulation_flag: break
                        if _sk == 'regr' and not regression_flag: break
                        if _sk == 'dumpwave' and (not cmd_line_args_dict['wave']) and (not cmd_line_args_dict['wall']): break
                    else:
                        _main_key = _sk if not _main_key else _main_key+'_'+_sk
                if _main_key and cmd_line_args_dict['debug']: print('handling '+_main_key)
                if _main_key in {'SOURCE_CFG'}:
                    f_parse_config_file(_value)
                elif _main_key in {'CUSTOM_SWITCH'}: #CUSTOM_SWITCH: usrarg, value:ON, default:ON, append:OFF
                    cfg_file_items_dict[_main_key.lower()].append(_value)
                    _csl = _value.replace(',','').split()
                    _name = _csl[0]
                    _valuable = False
                    _default = False
                    _append = True
                    for _z in _csl:
                        if 'value:' in _z.lower(): _valuable = True if 'ON' in _z else False
                        if 'default:' in _z.lower(): _default = True if 'ON' in _z else False
                        if 'append:' in _z.lower(): _append = True if 'ON' in _z else False
                    if not _name in custom_switch_in_cfg_file_dict.keys():
                        custom_switch_in_cfg_file_dict[_name] = [_valuable, _default, _append] #FIXME: seems _valuable is useless
                elif _main_key in {'DESIGN_TOP', 'TB_TOP'}:
                    cfg_file_items_dict[_main_key.lower()] = _value
                elif _main_key in {'INC_DIR', 'DESIGN_FILES', 'DV_FILES', 'LIB_FILES', 'MODEL_FILES'}:
                    cfg_file_items_dict[_main_key.lower()].append(_value)
                elif _main_key in {'TIME_SCALE', 'UVM_TIMEOUT', 'MAX_QUIT_COUNT', 'COMPILE_REPEAT_TIMES'}:
                    cfg_file_items_dict[_main_key.lower()] = _value
                elif _main_key in {'BLK_ROOT', 'BLK_DESIGN_ROOT', 'BLK_DV_ROOT'}:
                    cfg_file_items_dict[_main_key.lower()] = os.path.expandvars(_value)
                elif _main_key in {'TCL_FILES', 'TFILES'}:
                    cfg_file_items_dict[_main_key.lower()].append(os.path.expandvars(_value))
                elif _main_key in {'BSUB_OPT', 'EXT_OPT', 'EXT_COMP_OPT', 'EXT_SIM_OPT', 'EXT_DBG_OPT'}:
                    cfg_file_items_dict[_main_key.lower()].append(_value)
                elif _main_key in {'PRE_COMP_CMD', 'POST_COMP_CMD', 'PRE_SIM_CMD', 'POST_SIM_CMD'}:
                    cfg_file_items_dict[_main_key.lower()].append(_value)
                elif _main_key in {'COV_TYPE', 'COV_FILES', 'COV_DUT', 'COV_REFINE_FILES'}:
                    cfg_file_items_dict[_main_key.lower()].append(_value)
                elif _main_key in {'WARN_STR', 'IGNORE_WARN_STR', 'ERR_STR', 'IGNORE_ERR_STR'}:
                    cfg_file_items_dict[_main_key.lower()].append(_value)
                elif _main_key in {'OTHER_SIM_LOG_FILES'}:
                    cfg_file_items_dict[_main_key.lower()].append(_value)
                elif _main_key in {'MAX_QUIT_COUNT'}:
                    cfg_file_items_dict['max_quit_count'] = int(_value)
                elif _main_key:
                    f_colorful_print('Unknown Key: '+_main_key, 'red')
                    print()
    #post process of cfgs
    if not cfg_file_items_dict['design_top'] or not cfg_file_items_dict['tb_top']: sys.exit('design_top/tb_top not defined in cfg file')
    #post process
    if cfg_file_items_dict['blk_root']: global_defines.append('_BLK_ROOT_=\\\"'+cfg_file_items_dict['blk_root']+'\\\"')
    if cfg_file_items_dict['blk_design_root']: global_defines.append('_BLK_DESIGN_ROOT_=\\\"'+cfg_file_items_dict['blk_design_root']+'\\\"')
    if cfg_file_items_dict['blk_dv_root']: global_defines.append('_BLK_DV_ROOT_=\\\"'+cfg_file_items_dict['blk_dv_root']+'\\\"')
    if cmd_line_args_dict['simulator'] == 'vcs':
        global_defines.append('_DESIGN_TOP_='+cfg_file_items_dict['design_top'])
        global_defines.append('_TB_TOP_='+cfg_file_items_dict['tb_top'])
    else:
        global_defines.append('_DESIGN_TOP_=\\\"'+cfg_file_items_dict['design_top']+'\\\"')
        global_defines.append('_TB_TOP_=\\\"'+cfg_file_items_dict['tb_top']+'\\\"')

def f_gen_folders():
    global generated_folders_info_dict
    global global_info_msg
    global sim_base_dir
    _path_of_test = ''
    if localdv_flag:
        sim_base_dir = os.path.expandvars(cmd_line_args_dict['sim_root'])+'/'+cmd_line_args_dict['block']+'/'+cmd_line_args_dict['dv_folder']
    elif single_simulation_flag:
        if cmd_line_args_dict['block']:
            _path_of_test = f_find_file(env_prj_root, cmd_line_args_dict['test'][0]+'/'+cmd_line_args_dict['test'][0]+'.sv', cmd_line_args_dict['block']+'/'+cmd_line_args_dict['dv_folder']+'/tests')
        else:
            _path_of_test = f_find_file(env_prj_root+'/'+cmd_line_args_dict['dv_folder']+'/tests', cmd_line_args_dict['test'][0]+'/'+cmd_line_args_dict['test'][0]+'.sv')
        if not _path_of_test: sys.exit(cmd_line_args_dict['test'][0]+'.sv not exist') #FIXME when there's only C test in folder
        sim_base_dir = os.path.expandvars(cmd_line_args_dict['sim_root'])+'/'+cmd_line_args_dict['block']+'/'+cmd_line_args_dict['test'][0]
        if cmd_line_args_dict['sim_type'] != 'rtl':
            sim_base_dir += '_'+cmd_line_args_dict['sim_type']
    elif regression_flag:
        f_gen_regr_list()
        sim_base_dir = os.path.expandvars(cmd_line_args_dict['sim_root'])+'/'+cmd_line_args_dict['block']+'/'+cmd_line_args_dict['daily_folder']+'/regr_'+(''.join(cmd_line_args_dict['regr_group']).lower())+'_'+time_label
    if cmd_line_args_dict['sim_folder']: sim_base_dir = os.path.expandvars(cmd_line_args_dict['sim_folder']) #override sim_base_dir when -d is used with script
    else:
        sim_base_dir += cmd_line_args_dict['append_dir_name'] #there is '_' already in cmd_line_args_dict['append_dir_name'] if -append is used in cmd line
        if single_simulation_flag:
            for _z in custom_switch_in_cfg_file_dict.keys():
                if _z in custom_switch_on_cmd_line_dict.keys():
                    if custom_switch_in_cfg_file_dict[_z][2] and (custom_switch_on_cmd_line_dict[_z] != '_disable'): #if custom switch is ON from cmd line
                        sim_base_dir += '_'+_z.lower()
                elif custom_switch_in_cfg_file_dict[_z][1] and custom_switch_in_cfg_file_dict[_z][2]: #if custom switch is ON by default
                    sim_base_dir += '_'+_z.lower()
    global_info_msg.append(sim_base_dir)
    for _z in custom_switch_in_cfg_file_dict.keys():
        if _z in custom_switch_on_cmd_line_dict.keys():
            if custom_switch_on_cmd_line_dict[_z] == '_disable': #if custom switch is ON from cmd line
                f_colorful_print('Custom switch('+_z+'): OFF', 'red')
                print()
            elif custom_switch_on_cmd_line_dict[_z] == '_valueless':
                f_colorful_print('Custom switch('+_z+'): ON', 'green')
                print()
            else:
                f_colorful_print('Custom switch('+_z+'): ON, Value:'+custom_switch_on_cmd_line_dict[_z], 'green')
                print()
        elif custom_switch_in_cfg_file_dict[_z][1]: #if custom switch is ON by default
            f_colorful_print('Custom switch('+_z+'): ON (by default)', 'green')
            print()
        else:
            f_colorful_print('Custom switch('+_z+'): OFF (by default)', 'red')
            print()
    if sim_base_dir:
        if cmd_line_args_dict['clean'] and os.path.exists(sim_base_dir): shutil.rmtree(sim_base_dir, ignore_errors=True)
        os.makedirs(sim_base_dir, exist_ok=True)
        if os.path.isfile(sim_base_dir+'/_ERROR_'): os.remove(sim_base_dir+'/_ERROR_') #remove some files
        if os.path.isfile(sim_base_dir+'/_WARN_'): os.remove(sim_base_dir+'/_WARN_')
        if os.path.isfile(sim_base_dir+'/_PASS_'): os.remove(sim_base_dir+'/_PASS_')
        os.chmod(sim_base_dir, 0o755)
        print(sim_base_dir)
        if localdv_flag:
            f_gen_eda_wrapper_scripts(sim_base_dir, _path_of_test)
            generated_folders_info_dict[sim_base_dir] = {} #extra info will be filled into the list
            generated_folders_info_dict[sim_base_dir]['done'] = False
            generated_folders_info_dict[sim_base_dir]['test'] = cmd_line_args_dict['dv_folder']
            generated_folders_info_dict[sim_base_dir]['seed'] = 0
            generated_folders_info_dict[sim_base_dir]['parent'] = sim_base_dir
            generated_folders_info_dict[sim_base_dir]['script'] = ' '.join(sys.argv)
        elif single_simulation_flag:
            f_gen_eda_wrapper_scripts(sim_base_dir, _path_of_test)
            generated_folders_info_dict[sim_base_dir] = {} #extra info will be filled into the list
            generated_folders_info_dict[sim_base_dir]['done'] = False
            generated_folders_info_dict[sim_base_dir]['test'] = cmd_line_args_dict['test'][0]
            generated_folders_info_dict[sim_base_dir]['seed'] = int(cmd_line_args_dict['seed'])
            generated_folders_info_dict[sim_base_dir]['parent'] = sim_base_dir
            if ('-s' in sys.argv) or ('-seed' in sys.argv):
                generated_folders_info_dict[sim_base_dir]['script'] = ' '.join(sys.argv)
            else:
                generated_folders_info_dict[sim_base_dir]['script'] = ' '.join(sys.argv)+' -s '+str(cmd_line_args_dict['seed'])
        elif regression_flag:
            with open(sim_base_dir+'/README', 'w+') as f: #print new generated regression list into a filee
                f.write('//generated @ ' + time_label + ' by ' + env_usr + ' from ' + env_hostname + '\n')
                f.write('\n//==== Input Arguements ====\n//')
                f.write('\n//'.join(sys.argv))
                f.write('\n//==== CMD LINE ====\n')
                f.write(str(cmd_line_args_dict))
                f.write('\n//==== CFG FILE ====\n')
                f.write(str(cfg_file_items_dict))
                f.write('\n')
                f.write('\n//==== Regression List ====\n')
                for _x in case_list_in_regression.keys():
                    for _y in case_list_in_regression[_x]:
                        f.write(_x+' '+_y['switch']+': S='+str(_y['repeat'])+'\n')
            _args_from_parent = ' '.join(cmd_line_args_dict['next_level_args'])
            for _x in case_list_in_regression.keys(): #_x is the test name in regression list
                if cmd_line_args_dict['block']:
                    _path_of_test = f_find_file(env_prj_root, _x+'/'+_x+'.sv', cmd_line_args_dict['block']+'/'+cmd_line_args_dict['dv_folder']+'/tests')
                else:
                    _path_of_test = f_find_file(env_prj_root+'/'+cmd_line_args_dict['dv_folder']+'/tests', _x+'/'+_x+'.sv')
                if not _path_of_test: sys.exit(_x+'.sv not exist')
                _num = 0
                for _y in case_list_in_regression[_x]:
                    for _z in range(_y['repeat']):
                        _num += 1
                        _sub_folder = sim_base_dir+'/'+_x+'_'+str(_num).zfill(5)
                        generated_folders_info_dict[_sub_folder] = {} #extra info will be filled into the list
                        generated_folders_info_dict[_sub_folder]['done'] = False
                        generated_folders_info_dict[_sub_folder]['test'] = _x
                        generated_folders_info_dict[_sub_folder]['parent'] = sim_base_dir
                        if ('-s ' in _args_from_parent+' '+_y['switch']) or ('-seed' in _args_from_parent+' '+_y['switch']): #if -s/-seed are in regression list
                            _switch_list = (_args_from_parent+' '+_y['switch']).lower().split()
                            _seed_index = -1 if not '-seed' in _switch_list else _switch_list.index('-seed')
                            _s_index = -1 if not '-s' in _switch_list else _switch_list.index('-s')
                            if _seed_index<_s_index: _seed_index = _s_index
                            _sub_seed = str(_switch_list[_seed_index+1])
                            _cmd = sys.argv[0]+' -t '+_x+' -[ '+_args_from_parent+' -] '+_y['switch']+' -d '+_sub_folder
                            generated_folders_info_dict[_sub_folder]['script'] = _cmd
                            generated_folders_info_dict[_sub_folder]['seed'] = int(_sub_seed)
                        else: #specify a seed for item in regression list
                            _sub_seed = str(random.randint(1,2147483647))
                            _cmd = sys.argv[0]+' -t '+_x+' -[ '+_args_from_parent+' -] '+_y['switch']+' -d '+_sub_folder+' -s '+_sub_seed
                            generated_folders_info_dict[_sub_folder]['script'] = _cmd
                            generated_folders_info_dict[_sub_folder]['seed'] = int(_sub_seed)
                        os.system('/usr/bin/python3 '+_cmd+' > /dev/null') #f_gen_eda_wrapper_scripts is called
    else: sys.exit('fail in folder generation')

    if regression_flag:
        if total_runs_in_regression != len(generated_folders_info_dict):
            sys.exit('Only '+str(len(generated_folders_info_dict))+' folders are created for '+str(total_runs_in_regression)+' runs')
    else:
        if 1 != len(generated_folders_info_dict):
            sys.exit('No folder generated')

def f_plot_curve(): #for daily regression, coverage merge and plot scripts are generated in upper level
    if cmd_line_args_dict['cov_merge']: #if -cov and -cm in cmd line
        with open(sim_base_dir+'/cover_merge.tcl', 'w+') as f: #generate merge coverage script, merge the coverage in one regression
            f.write('//imc -exec cover_merge.tcl\n')
            f.write('merge -overwrite\\\n')
            for folder in generated_folders_info_dict.keys():
                is_failed_case = True if generated_folders_info_dict[folder]['result'] == '_ERROR_' else False
                is_nocov_case = True if 'nocov' in generated_folders_info_dict[folder]['script'].lower() else False
                if is_failed_case or is_nocov_case:
                    f.write(folder+'\t/cov_work/scope/test_sv'+str(generated_folders_info_dict[folder]['seed'])+'\\\n')
            f.write('-out '+os.path.expandvars(sim_base_dir)+'/cov_work\n')
            f.write('load -run '+sim_base_dir+'/cov_wor\n')
            if cmd_line_args_dict['cov_refine_files'] or cfg_file_items_dict['cov_refine_files']:
                for cc in cmd_line_args_dict['cov_refine_files']:
                    if os.path.isdir(cc): f.write('load -refinement '+os.path.expandvars(cc)+'\n')
                for cc in cfg_file_items_dict['cov_refine_files']:
                    if os.path.isdir(cc): f.write('load -refinement '+os.path.expandvars(cc)+'\n')
            f.write('report -html -detail -metrics overall:all -overwrite -all -cumulative on -grading both -out '+sim_base_dir+'/cov_html\n')

        print('Waing for coverage merging')
        if cmd_line_args_dict['lsf']: #invoke imc to merge coverage
            os.system('bsub -J '+cmd_line_args_dict['lsf_job_group_name']+' -K -I \"imc -exec '+sim_base_dir+'/cover_merge.tcl\"')
        else:
            os.system('imc -exec '+sim_base_dir+'/cover_merge.tcl')
    else: pass #cover_merge

    if cmd_line_args_dict['daily_folder']: #if only daily_folder is specified
        print('Waing for ploting curve')
        overall_coverage_percentage = '0.00%'
        if os.path.isfile(sim_base_dir+'/cov_html/index.html'): #grep overall coverage
            overall_average_line = False
            with open(sim_base_dir+'/cov_html/index.html', 'r') as f:
                for _line in f:
                    if overall_average_line:
                        if '<TR><TD class=' in _line:
                            overall_coverage_percentage = re.sub(r'<.*>', r'', re.sub(r'</TD>', r'', line.replace('\n','').replace('\t','').strip()))
                            break
                    if 'Overall Average' in _line: overall_average_line = True

        date_str = datetime.datetime.now().strftime('%Y/%m/%d')
        echo_string = overall_coverage_percentage+' '+str(pass_runs_in_regression)+' '+str(warn_runs_in_regression)+' '+str(error_runs_in_regression)+' '+str(total_runs_in_regression)+' '+date_str+' '+sim_base_dir
        if not os.path.isfile(sim_base_dir+'/../_daily.data'):
            os.system('echo \"Cover Pass Warn Fail Total Date Path\" > '+sim_base_dir+'/../_daily.data')
        os.system('echo \"'+echo_string+'\" >> '+sim_base_dir+'/../_daily.data')

        with open(sim_base_dir+'/../gnuplot_curve.gp', 'w+') as f: #generate gnu plot script
            f.write('set terminal pngcairo size 800, 600\n')
            f.write('set output \"'+os.path.expandvars(sim_base_dir)+'/../_regression.png\"\n')
            f.write('set title \"Regression Grading\"\n')
            f.write('set grid xtics ytics\n')
            f.write('set grid linestyle 1 lc rgb \"#dddddd\"\n')
            f.write('set grid back\n')
            f.write('set label \"Last update: '+time_label+'\" at screen 0.1, 0.08 center font \",10\" tc rgb \"red\"\n')
            f.write('set key below center\n')
            f.write('set key autotitle columnhead\n')
            f.write('set style data lines\n')
            f.write('set xlabel \"Date\"\n')
            f.write('set timefmt \"%Y/%m/%d\"\n')
            f.write('set format x \"%Y/%m/%d\"\n')
            f.write('set xdata time\n')
            f.write('set xtics rotate out\n')
            f.write('set xtics 86400*7\n')
            f.write('set ylabel \"Coverage (%)\"\n')
            f.write('set yrange [0:100]\n')
            f.write('set y2label \"Count\"\n')
            f.write('set y2range [0:*]\n')
            f.write('set y2tics nomirror\n')
            f.write('set y2tics 53\n')
            f.write('DATE_FORMAT = \"%Y/%m/%d\"\n')
            f.write('parse_date(string) = strptime(DATE_FORMAT, string)\n')
            f.write('plot \"'+os.path.expandvars(sim_base_dir)+'/../_daily.data\" using (parse_date(stringcolumn(6))):($1) title \"Cover\" lw 3 lt rgb \"blue\" axis x1y1, \\\n')
            f.write('\t\"\" using (parse_date(stringcolumn(6))):($2) title \"Pass\" lw 3 lt rgb \"green\" axis x1y2, \\\n')
            f.write('\t\"\" using (parse_date(stringcolumn(6))):($3) title \"Warn\" lw 3 lt rgb \"orange\" axis x1y2, \\\n')
            f.write('\t\"\" using (parse_date(stringcolumn(6))):($4) title \"Fail\" lw 3 lt rgb \"red\" axis x1y2, \\\n')
            f.write('\t\"\" using (parse_date(stringcolumn(6))):($5) title \"Total\" lw 3 lt rgb \"purple\" axis x1y2')

        os.system('gnuplot '+sim_base_dir+'/../gnuplot_curve.gp') #FIXME: path of gnuplot need to be updated

        html_header = '<title>Regression</title>\n<p><img src=\"'+os.path.expandvars(sim_base_dir)+'/../_regression.png\"></p>\n'
        html_string = '<p>'
        html_string = '<a href=\"'+os.path.expandvars(sim_base_dir)+'/cov_html/index.html\">'+date_str+'</a>'
        html_string += ' '+overall_coverage_percentage+'(P:'+str(pass_runs_in_regression)+'+W:'+str(warn_runs_in_regression)+'+F:'+str(error_runs_in_regression)+'=T:'+str(total_runs_in_regression)+') '
        html_string += os.path.expandvars(sim_base_dir)
        html_string += '</p>'
        if not os.path.isfile(sim_base_dir+'/../_daily.html'):
            os.system('echo \"'+html_header+'\" > '+sim_base_dir+'/../_daily.html')
        os.system('echo \"'+html_string+'\" > '+sim_base_dir+'/../_daily.html')

        cov_work_list = glob.glob(sim_base_dir+'/../*/cov_work')
        if cov_work_list:
            with open(sim_base_dir+'/../cover_merge.tcl', 'w+') as f: #generate merge coverage script, merge the coverage in all regressions in daily folder
                f.write('//imc -exec cover_merge.tcl\n')
                f.write('merge -overwrite\\\n')
                for cwl in cov_work_list: f.write(cwl+'\\\n')
                f.write('-out '+os.path.expandvars(sim_base_dir)+'/../cov_work\n')
                f.write('load -run '+sim_base_dir+'/../cov_work\n')
                if cmd_line_args_dict['cov_refine_files'] or cfg_file_items_dict['cov_refine_files']:
                    for cc in cmd_line_args_dict['cov_refine_files']:
                        if os.path.isdir(cc): f.write('load -refinement '+os.path.expandvars(cc)+'\n')
                    for cc in cfg_file_items_dict['cov_refine_files']:
                        if os.path.isdir(cc): f.write('load -refinement '+os.path.expandvars(cc)+'\n')
                f.write('report -html -detail -metrics overall:all -overwrite -all -cumulative on -grading both -out '+sim_base_dir+'/../cov_html\n')
            if cmd_line_args_dict['lsf']: #invoke imc to merge coverage
                os.system('bsub -J '+cmd_line_args_dict['lsf_job_group_name']+' -K -I \"imc -exec '+sim_base_dir+'/../cover_merge.tcl\"')
            else:
                os.system('imc -exec '+sim_base_dir+'/../cover_merge.tcl')

        print('Plot done')
    else: pass #daily_folder

def f_gen_eda_wrapper_scripts(sim_folder, test_path):
    f_timestamp_print_in_sim(sim_folder)

    _define_macros = ('+define+_RUN_DIR_=\\\"'+sim_folder+'\\\"') + '\\\n+define+' + ('\\\n+define+'.join(global_defines))
    _global_variables = ''
    _global_variables += 'setenv TMPDIR ' + cmd_line_args_dict['sim_tmp'] + '\n' + 'set tmpdir = ${TMPDIR}' + '\n'
    _global_variables += 'setenv PRJ_NAME ' + env_prj_name + '\n' + 'set prj_name = ${PRJ_NAME}' + '\n'
    _global_variables += 'setenv PRJ_ROOT ' + env_prj_root + '\n' + 'set prj_root = ${PRJ_ROOT}' + '\n'
    _global_variables += 'setenv DV_ROOT ' + env_dv_root + '\n' + 'set dv_root = ${DV_ROOT}' + '\n'
    _global_variables += 'setenv SIM_ROOT ' + env_sim_root + '\n' + 'set sim_root = ${SIM_ROOT}' + '\n'
    if cfg_file_items_dict['blk_root']: _global_variables += 'setenv BLK_ROOT ' + cfg_file_items_dict['blk_root'] + '\n' + 'set blk_root = ${BLK_ROOT}' + '\n'
    if cfg_file_items_dict['blk_design_root']: _global_variables += 'setenv BLK_DESIGN_ROOT ' + cfg_file_items_dict['blk_design_root'] + '\n' + 'set blk_design_root = ${BLK_DESIGN_ROOT}' + '\n'
    if cfg_file_items_dict['blk_dv_root']: _global_variables += 'setenv BLK_DV_ROOT ' + cfg_file_items_dict['blk_dv_root'] + '\n' + 'set blk_dv_root = ${BLK_DV_ROOT}' + '\n'
    _global_variables += 'set run_dir = ' + sim_folder + '\n'
    _global_variables += 'setenv run_dir ' + sim_folder + '\n'
    _global_variables += 'set case_name = ' + os.path.basename(test_path).replace('.sv', '') + '\n'
    _global_variables += 'set case_path = ' + test_path + '\n'
    _global_variables += 'set case_dir = ' + os.path.dirname(test_path) + '\n'
    _global_variables += 'set seed = ' + cmd_line_args_dict['seed'] + '\n'
    _global_variables += 'set repeat_times = ' + cmd_line_args_dict['compile_repeat_number'] + '\n'
    _global_variables += 'set date_str = `date +\"%y_%m_%d\"`' + '\n'
    _global_variables += 'set time_str = `date +\"%H%M%S\"`' + '\n'
    for _c, _v in cmd_line_args_dict['enable_custom_switch_valuable'].items(): #TODO
            _global_variables += 'set '+_c+' = '+_v+'\n'

    with open(sim_folder+'/README', 'a+') as f:
        f.write('//generated @ ' + time_label + ' by ' + env_usr + ' from ' + env_hostname + '\n')
        f.write('\n//==== Input Arguements ====\n')
        f.write(str(sys.argv))
        f.write('\n//==== Global Variables ====\n//')
        f.write(_global_variables)
        f.write('\n//==== Global Macros ====\n//')
        f.write(_define_macros)
        f.write('\n//==== CMD LINE ====\n')
        f.write(str(cmd_line_args_dict))
        f.write('\n//==== CFG FILE ====\n')
        f.write(str(cfg_file_items_dict))
        f.write('\n')
    
    with open(sim_folder+'/compile.sh', 'w+') as f:
        f.write('#! /bin/csh\n')
        f.write(_global_variables)
        f.write('\n')
        f.write('\\rm -rf _COMP_DONE_ _SIM_DONE_\n')
        f.write('\n')
        f.write('#Pre-compile\n')
        f.write('\n'.join(cfg_file_items_dict['pre_comp_cmd']))
        f.write('\n\n')
        f.write('if (-e $run_dir/comp.log-1) then\n')
        f.write('\trm -rf $run_dir/comp.log-*\n')
        f.write('endif\n')
        f.write('\n')
        f.write('if ($#argv>0) then\n') #get repeat_times from command line
        f.write('\tset repeat_times = $argv[1]\n')
        f.write('endif\n')
        f.write('\n')
        f.write('set retries = 0\n')
        f.write('while ($retries <= $repeat_times)\n')
        f.write('\t@ retries++\n')
        if cmd_line_args_dict['simulator'] == 'nc': #TODO
            f.write('xrun -nocopyright -64bit -sv -sysv\\\n')
            f.write('-sysv_ext .v,.vh,.sv,.svh,.svi,.svp,.sva,.vm,.vg,.pkg,.mv,.SVM\\\n') #FIXME
            f.write('-elaborate\\\n')
            if cmd_line_args_dict['sim_tmp']: f.write('-simtmp '+cmd_line_args_dict['sim_tmp']+'\\\n')
            if cmd_line_args_dict['wave'] or cmd_line_args_dict['wall']:
                f.write('+access+rwc\\\n')
                f.write('-linedebug -fsmdebug\\\n') #verbose
                if cmd_line_args_dict['uvm']: f.write('-uvmlinedebug\\\n') #verbose
                if cmd_line_args_dict['wave_type'] == 'fsdb': f.write('+fsdb+delta\\\n') #verbose
            if cmd_line_args_dict['uvm']: f.write('-uvm -uvmnocdnsextra\\\n')
            if cmd_line_args_dict['tfiles'] or cfg_file_items_dict['tfiles']: #for gls
                f.write('-entfileenv -tfverbose\\\n') #verbose
                if cmd_line_args_dict['tfiles']: f.write(('-tfile '+' -tfile '.join(cmd_line_args_dict['tfiles']))+'\\\n')
                if cfg_file_items_dict['tfiles']: f.write(('-tfile '+' -tfile '.join(cfg_file_items_dict['tfiles']))+'\\\n')
            if cmd_line_args_dict['tcl_files']: f.write(('-input '+' -input '.join(cmd_line_args_dict['tcl_files']))+'\\\n')
            elif cmd_line_args_dict['wave'] or cmd_line_args_dict['wall']: f.write('-input $run_dir/dump_wave.tcl\\\n')
            if cfg_file_items_dict['tcl_files']: f.write(('-input '+' -input '.join(cfg_file_items_dict['tcl_files']))+'\\\n')
            f.write('-timescale '+cfg_file_items_dict['time_scale']+'\\\n')
            f.write(_define_macros+'\\\n')
            if cmd_line_args_dict['automsg']: f.write('$run_dir/automsg.sv $run_dir/date.c\\\n')
            f.write('-top '+cfg_file_items_dict['tb_top']+'\\\n')
            f.write(' '.join(cmd_line_args_dict['plus_args'])+'\\\n')
            f.write(' '.join(cmd_line_args_dict['extra_comp_options'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_opt'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_comp_opt'])+'\\\n')
            if cmd_line_args_dict['cov_enable']:
                f.write('-covbaserun $case_name -covcleanworkdir\\\n')
                if cfg_file_items_dict['cov_type']:
                    f.write('-coverage '+' -coverage '.join(cfg_file_items_dict['cov_type'])+'\\\n')
                else: f.write('-coverage all\\\n')
                f.write('-covfile '+' -covfile '.join(cfg_file_items_dict['cov_files'])+'\\\n')
                if cfg_file_items_dict['cov_dut']:
                    f.write('-covdut '+' -covdut '.join(cfg_file_items_dict['cov_dut'])+'\\\n')
                else: f.write('-covdut '+cfg_file_items_dict['tb_top']+'\\\n')
            if cfg_file_items_dict['inc_dir']:
                f.write(' +incdir+' + ' +incdir+'.join(cfg_file_items_dict['inc_dir'])+'\\\n')
            f.write('+incdir+$case_dir +incdir+./\\\n')
            f.write(' '.join(cfg_file_items_dict['lib_files'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['model_files'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['design_files'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['dv_files'])+'\\\n')
            if cmd_line_args_dict['uvm']: f.write('$case_path\\\n')
            if cmd_line_args_dict['sim_on_gui']: f.write('-gui\\\n')
            if regression_flag or cmd_line_args_dict['single_in_regr']:
                f.write('-nostdout -l $run_dir/comp.log\n')
            else:
                f.write('-l $run_dir/comp.log\n')
        if cmd_line_args_dict['simulator'] == 'vcs': #TODO
            #f.write('vcs -full64 -v2k -sverilog -licqueue -lca +systemverilogext+.v +vcs+flush+log +vcs+lic+wait +vcs+fsdbon\\\n')
            #f.write('-timescale=1ns/1fs +lint=TFIPC-L -Xgc=+ -fastcomp=il -kdb -debug_all -ntb_opts uvm-1.1\\\n')
            #f.write('-cm line+cond+fsm+tgl+path+branch+assert -cm_hier [file] -o $run_dir/simv\n')
            f.write('vcs -full64 +v2k -sverilog +systemverilogext+.v+.sv+.svh+.vh+.svi+.svp+.sva+.vm+.vg+.pkg+.mv+.SVM -lca\\\n')
            f.write('+vcs+flush+log +vcs+lic+wait -Xgc=+ -fastcomp=il -kdb -assert svaext\\\n')
            if cmd_line_args_dict['cov_enable']:
                f.write('-cm cond+tgl+line+fsm+branch+assert -cm_line contassign -cm_cond allops+anywidth+event -cm_tgl mda -cm_noconst\\\n')
                #f.write('-cm_hier'+??+'\\\n')
            if cmd_line_args_dict['uvm']: f.write('-ntb_opts uvm-1.1\\\n')
            f.write('-timescale='+cfg_file_items_dict['time_scale']+'\\\n')
            if cmd_line_args_dict['wave'] or cmd_line_args_dict['wall']:
                f.write('-debug_access+all -debug_region+cell+lib+encrypt\\\n');
                f.write('-P $VERDI_HOME/share/PLI/VCS/LINUX64/novas.tab $VERDI_HOME/share/PLI/VCS/LINUX64/pli.a\\\n'); #seems not necessary for dump fsdb
                if cmd_line_args_dict['wave_type'] == 'fsdb':
                    f.write('-fsdb +define+FSDB +vcs+fsdbon+all +define+UVM_VERDI_COMPWAVE\\\n');
            f.write(_define_macros+'\\\n')
            if cmd_line_args_dict['automsg']: f.write('$run_dir/automsg.sv $run_dir/date.c\\\n')
            f.write('-top '+cfg_file_items_dict['tb_top']+'\\\n')
            f.write(' '.join(cmd_line_args_dict['plus_args'])+'\\\n')
            f.write(' '.join(cmd_line_args_dict['extra_comp_options'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_opt'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_comp_opt'])+'\\\n')
            if cfg_file_items_dict['inc_dir']:
                f.write(' +incdir+' + ' +incdir+'.join(cfg_file_items_dict['inc_dir'])+'\\\n')
            f.write('+incdir+$case_dir +incdir+./\\\n')
            f.write(' '.join(cfg_file_items_dict['lib_files'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['model_files'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['design_files'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['dv_files'])+'\\\n')
            if cmd_line_args_dict['uvm']: f.write('$case_path\\\n')
            if cmd_line_args_dict['sim_on_gui']: f.write('-gui\\\n')
            if regression_flag or cmd_line_args_dict['single_in_regr']:
                f.write('+vcs+nostdout -l $run_dir/comp.log\n')
            else:
                f.write('-l $run_dir/comp.log\n')
        f.write('\tif ($? == 0) then\n')
        f.write('\t\tbreak\n')
        f.write('\telse\n')
        f.write('\t\tgrep \"\\*F,INTERR\" $run_dir/comp.log\n')
        f.write('\t\tif ($? == 0) then\n')
        f.write('\t\t\t\\cp $run_dir/comp.log $run_dir/comp.log-$retries\n')
        f.write('\t\telse\n')
        f.write('\t\t\tbreak\n')
        f.write('\t\tendif\n')
        f.write('\tendif\n')
        f.write('end #while\n') #while
        f.write('\n')
        f.write('#Post-compile\n')
        f.write('\n'.join(cfg_file_items_dict['post_comp_cmd']))
        f.write('\n\n')
        f.write('\\touch _COMP_DONE_\n')
    os.chmod(sim_folder+'/compile.sh', 0o744)

    with open(sim_folder+'/simulate.sh', 'w+') as f:
        f.write('#! /bin/csh\n')
        f.write(_global_variables)
        f.write('\n')
        f.write('\\rm -rf _SIM_DONE_\n')
        f.write('\n')
        f.write('#Pre-simulate\n')
        f.write('\n'.join(cfg_file_items_dict['pre_sim_cmd']))
        f.write('\n\n')
        f.write('if ($#argv>0) then\n') #get repeat_times from command line
        f.write('\tset seed = $argv[1]\n')
        f.write('endif\n')
        f.write('\n')
        f.write('\\ln -fs $run_dir/sim_${date_str}__${time_str}_seed$seed.log $run_dir/latest_sim.log\n')
        if cmd_line_args_dict['simulator'] == 'nc':
            f.write('xrun -nocopyright -64bit -R\\\n')
            if cmd_line_args_dict['sim_tmp']: f.write('-simtmp '+cmd_line_args_dict['sim_tmp']+'\\\n')
            if cmd_line_args_dict['max_quit_count'] > -1:
                f.write('-errormax '+str(cmd_line_args_dict['max_quit_count'])+'\\\n')
                f.write('+UVM_MAX_QUIT_COUNT='+str(cmd_line_args_dict['max_quit_count'])+'\\\n')
            elif cfg_file_items_dict['max_quit_count'] > -1:
                f.write('-errormax '+str(cfg_file_items_dict['max_quit_count'])+'\\\n')
                f.write('+UVM_MAX_QUIT_COUNT='+str(cfg_file_items_dict['max_quit_count'])+'\\\n')
            else:
                f.write('-errormax 100\\\n')
                f.write('+UVM_MAX_QUIT_COUNT=100\\\n')
            f.write('+UVM_TIMEOUT='+cfg_file_items_dict['uvm_timeout']+',NO\\\n')
            f.write('+UVM_TESTNAME=$case_name\\\n')
            if cmd_line_args_dict['cov_enable']:
                f.write('-covoverwrite -covworkdir $run_dir/cov_work\\\n')
            f.write('-seed $seed +seed=$seed\\\n')
            f.write(' '.join(cmd_line_args_dict['plus_args'])+'\\\n')
            f.write(' '.join(cmd_line_args_dict['extra_sim_options'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_opt'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_sim_opt'])+'\\\n')
            if regression_flag or cmd_line_args_dict['single_in_regr']:
                f.write('-nostdout -l $run_dir/sim_${date_str}__${time_str}_seed$seed.log\n')
            else:
                f.write('-l $run_dir/sim_${date_str}__${time_str}_seed$seed.log\n')
        if cmd_line_args_dict['simulator'] == 'vcs':
            if cmd_line_args_dict['wave'] or cmd_line_args_dict['wall']:
                if cmd_line_args_dict['wave_type'] == 'fsdb':
                    f.write('\\ln -fs $run_dir/novas.fsdb $run_dir/waves.fsdb\n')
            f.write('$run_dir/simv\\\n')
            if cmd_line_args_dict['wave'] or cmd_line_args_dict['wall']:
                if cmd_line_args_dict['wave_type'] == 'fsdb':
                    f.write('+fsdb+autoflush +fsdb+dump_limit=1024 +fsdb+dump_log=on\\\n')
                    f.write('+fsdb+delta +fsdbfile+novas\\\n')
            if cmd_line_args_dict['cov_enable']:
                f.write('-cm cond+tgl+line+fsm+branch+assert -cm_name $case_name\\\n')
                #f.write('-cm_hier'+??+'\\\n')
            if cmd_line_args_dict['max_quit_count'] > -1:
                f.write('+UVM_MAX_QUIT_COUNT='+str(cmd_line_args_dict['max_quit_count'])+'\\\n')
            elif cfg_file_items_dict['max_quit_count'] > -1:
                f.write('+UVM_MAX_QUIT_COUNT='+str(cfg_file_items_dict['max_quit_count'])+'\\\n')
            else:
                f.write('+UVM_MAX_QUIT_COUNT=100\\\n')
            f.write('+UVM_TIMEOUT='+cfg_file_items_dict['uvm_timeout']+',NO\\\n')
            f.write('+UVM_TESTNAME=$case_name\\\n')
            f.write(' '.join(cmd_line_args_dict['plus_args'])+'\\\n')
            f.write(' '.join(cmd_line_args_dict['extra_sim_options'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_opt'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_sim_opt'])+'\\\n')
            f.write('-l $run_dir/sim_${date_str}__${time_str}_seed$seed.log\n')
            if cmd_line_args_dict['wave'] or cmd_line_args_dict['wall']:
                if cmd_line_args_dict['wave_type'] == 'fsdb':
                    f.write('\\ln -fs $run_dir/novas.fsdb $run_dir/waves.fsdb\n')
        f.write('\\ln -fs $run_dir/sim_${date_str}__${time_str}_seed$seed.log $run_dir/latest_sim.log\n')
        f.write('\n')
        f.write('#Post-simulate\n')
        f.write('\n'.join(cfg_file_items_dict['post_sim_cmd']))
        f.write('\n\n')
        f.write('\\touch _SIM_DONE_\n')
    os.chmod(sim_folder+'/simulate.sh', 0o744)

    with open(sim_folder+'/guidebug.sh', 'w+') as f:
        f.write('#! /bin/csh\n')
        f.write(_global_variables)
        f.write('\n')
        f.write('\n')
        if cmd_line_args_dict['wave_type'] == 'shm':
            f.write('simvision -64BIT -TITLE \"$case_name [$run_dir]\"\\\n')
            f.write(' '.join(cmd_line_args_dict['extra_dbg_options'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_dbg_opt'])+'\\\n')
            f.write('-LOGFILE $run_dir/simvision.log $run_dir/waves.shm&\n')
        elif cmd_line_args_dict['wave_type'] == 'vcd':
            f.write('simvision -64BIT -TITLE \"$case_name [$run_dir]\"\\\n')
            f.write(' '.join(cmd_line_args_dict['extra_dbg_options'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_dbg_opt'])+'\\\n')
            f.write('-LOGFILE $run_dir/simvision.log $run_dir/waves.vcd&\n')
        elif cmd_line_args_dict['wave_type'] == 'fsdb':
            f.write('verdi -sv -2001 -2012 -logfile $run_dir/verdiLog/verdi.log -logdir $run_dir/verdiLog\\\n')
            if cmd_line_args_dict['uvm']:
                f.write('-uvmDebug -ntb_opts uvm-1.1 -uvm\\\n')
            f.write('+systemverilogext+.v+.vh+.sv+.svh+.svi+.svp+.pkg+.SVM -ssv -ssy -ssz\\\n')
            if cfg_file_items_dict['inc_dir']:
                f.write(' +incdir+' + ' +incdir+'.join(cfg_file_items_dict['inc_dir'])+'\\\n')
            f.write('+incdir+$case_dir +incdir+./\\\n')
            f.write('-f $run_dir/'+cfg_file_items_dict['tb_top']+'.f\\\n')
            f.write(' '.join(cmd_line_args_dict['extra_dbg_options'])+'\\\n')
            f.write(' '.join(cfg_file_items_dict['ext_dbg_opt'])+'\\\n')
            f.write('-ssf $run_dir/waves.fsdb&\n')
        f.write('\n')
    os.chmod(sim_folder+'/guidebug.sh', 0o755)

    if (cmd_line_args_dict['simulator'] == 'vcs') and cmd_line_args_dict['cov_enable']:
        with open(sim_folder+'/covgui.sh', 'w+') as f:
            f.write('#! /bin/csh\n')
            f.write(_global_variables)
            f.write('\n')
            f.write('\n')
            f.write('verdi -cov -covdir $run_dir/simv.vdb&\n')
        os.chmod(sim_folder+'/covgui.sh', 0o755)

    if cmd_line_args_dict['simulator'] == 'nc':
        with open(sim_folder+'/dump_wave.tcl', 'w+') as f:
            if cmd_line_args_dict['wave_type'] == "shm":
                f.write('database -open waves -into '+sim_folder+'/waves.shm -incsize 2G -event -default\n')
                f.write('probe -create -packed 0 -shm -all -dynamic -memories -depth all\n')
                f.write('run\n')
            elif cmd_line_args_dict['wave_type'] == "fsdb":
                f.write('call fsdbAutoSwitchDumpfile 2048 '+sim_folder+'/waves.fsdb 50 '+sim_folder+'/waves.log\n')
                f.write('call fsdbDumpvars \"all\"\n')
                f.write('run\n')
            elif cmd_line_args_dict['wave_type'] == "vcd":
                f.write('database -open waves -vcd -into '+sim_folder+'/waves.vcd -event -default\n')
                f.write('probe -create -packed 0 -vcd -all -dynamic -memories -depth all\n')
                f.write('run\n')
    
    with open(sim_folder+'/'+cfg_file_items_dict['tb_top']+'.f', 'w+') as f: #TODO, need update
        f.write(_define_macros+'\n')
        f.write('-top '+cfg_file_items_dict['tb_top']+'\n')
        f.write(' '.join(cmd_line_args_dict['plus_args']))
        f.write(' '.join(cfg_file_items_dict['lib_files'])+'\n')
        f.write(' '.join(cfg_file_items_dict['model_files'])+'\n')
        f.write(' '.join(cfg_file_items_dict['design_files'])+'\n')
        f.write(' '.join(cfg_file_items_dict['dv_files'])+'\n')
        if cmd_line_args_dict['automsg']: f.write('$run_dir/automsg.sv\n')
        if cmd_line_args_dict['uvm']: f.write(test_path+'\n')

def f_gen_regr_list(): #gen a new list and store in regr folder
    global case_list_in_regression
    global total_runs_in_regression
    global cmd_line_args_dict #update ['regr'] when nested regr list is there
    for _t in cmd_line_args_dict['test']: #add individual test into new regression list
        if _t in case_list_in_regression.keys():
            _has_matched_item = False
            for _i, _c in enumerate(case_list_in_regression[_t]): #case_list_in_regression[_t] is a list, while _i is the index, and _c is the value which is a dict in the context
                if not _c['switch']:
                    _has_matched_item = True
                    case_list_in_regression[_t][_i]['repeat'] += cmd_line_args_dict['repeat_times']
                    break
            if not _has_matched_item:
                case_list_in_regression[_t].append({'switch': '', 'repeat': cmd_line_args_dict['repeat_times']})
        else:
            case_list_in_regression[_t] = []
            case_list_in_regression[_t].append({'switch': '', 'repeat': cmd_line_args_dict['repeat_times']})
    for _r in cmd_line_args_dict['regr']: #handle 'source:' in existing regression list
        if os.path.exists(_r):
            _path_of_r = _r
        elif cmd_line_args_dict['block']:
            _path_of_r = f_find_file(env_prj_root, cmd_line_args_dict['block']+'/'+cmd_line_args_dict['dv_folder']+'/regr/'+_r)
        else:
            _path_of_r = f_find_file(env_prj_root+'/'+cmd_line_args_dict['dv_folder'], 'regr/'+_r)
        if os.path.exists(_path_of_r):
            with open(_path_of_r, 'r') as f:
                for _line in f:
                    _line = str(_line).replace('\n', '').replace('\t', '').strip()
                    if len(_line) == 0: continue
                    if _line.startswith('source:'):
                        cmd_line_args_dict['regr'].extend(_line.replace('source:', '').split())
        else: sys.exit(_path_of_r+' not exist')
    for _r in cmd_line_args_dict['regr']: #add tests in existing regression list into new regression list
        if os.path.exists(_r):
            _path_of_r = _r
        elif cmd_line_args_dict['block']:
            _path_of_r = f_find_file(env_prj_root, cmd_line_args_dict['block']+'/'+cmd_line_args_dict['dv_folder']+'/regr/'+_r)
        else:
            _path_of_r = f_find_file(env_prj_root+'/'+cmd_line_args_dict['dv_folder'], 'regr/'+_r)
        with open(_path_of_r, 'r') as f:
            for _line in f:
                _line = str(_line).replace('\n', '').replace('\t', '').strip()
                if len(_line) == 0: continue
                if _line[0].isalnum():
                    if not ':' in _line: _line += ':'
                    _c, _g = _line.split(':')
                    _tmp_c = _c.split()
                    _testname = _tmp_c[0] # test name
                    _switch = ' '.join(_tmp_c[1:]) # extra switches in regression list
                    _g = re.sub(r'\s*=\s*', '=', _g)
                    _tmp_g = _g.split()
                    _repeat = 0
                    for _i in cmd_line_args_dict['regr_group']:
                        for _j in _tmp_g:
                            if _j.lower().startswith(_i.lower()+'='):
                                _repeat += int(_j.split('=')[1])
                    if '-repeat' in sys.argv: _repeat = cmd_line_args_dict['repeat_times'] #FIXME: check if -repeat is used in command line
                    if _repeat:
                        if _testname in case_list_in_regression.keys():
                            _has_matched_item = False
                            for _i, _j in enumerate(case_list_in_regression[_testname]):
                                if set(_j['switch'].split()) == set(_switch.split()):
                                    _has_matched_item = True
                                    case_list_in_regression[_testname][_i]['repeat'] += _repeat
                                    break
                            if not _has_matched_item:
                                case_list_in_regression[_testname].append({'switch': _switch, 'repeat': _repeat})
                        else:
                            case_list_in_regression[_testname] = []
                            case_list_in_regression[_testname].append({'switch': _switch, 'repeat': _repeat})
    if True: #randomize the order of tests in regression list
        keys = list(case_list_in_regression.keys())
        random.shuffle(keys)
        shuffled_dict = {key: case_list_in_regression[key] for key in keys}
        case_list_in_regression = shuffled_dict
    if case_list_in_regression: #print cases in regression list
        print('\n')
        print('-'*88)
        print('|{0:12}|{1:50}|{2}'.format('Runs', 'Test Names', 'Extra Options'))
        print('-'*88)
        for _x in case_list_in_regression.keys():
            for _y in case_list_in_regression[_x]:
                total_runs_in_regression += _y['repeat']
                print('|* {0:10}|{1:50}|{2}'.format(str(_y['repeat']), _x, _y['switch']))
        print('-'*88)
        print('|{0:12}|{1}'.format('Total', str(total_runs_in_regression)))
        print('-'*88)
        print('\n')
    else: sys.exit('no test in regression list is selected')

def f_find_file(parent_folder, file_with_path, other_match_pattern=''):
    _file_name = os.path.basename(file_with_path)
    for _root, _lists, _files in os.walk(parent_folder):
        for _file in _files:
            if _file_name == _file:
                _full_path = os.path.join(_root, _file)
                if ('/'+file_with_path in _full_path) and (other_match_pattern in _full_path):
                    if cmd_line_args_dict['debug']: print(_full_path)
                    return _full_path
    return ''

def f_start_running():
    global thread_list
    global generated_folders_info_dict
    for _f in generated_folders_info_dict.keys(): #generate cmd and logs list
        comp_cmd = _f+'/compile.sh'
        sim_cmd = _f+'/simulate.sh'
        run_cmd = ''
        var_cmd = ''
        lsf_cmd = ''
        full_cmd = ''
        logs_to_be_parsed = []
        if cmd_line_args_dict['compile_only']:
            run_cmd = 'cd '+_f+' && /bin/csh '+comp_cmd+' '+cmd_line_args_dict['compile_repeat_number']
        else:
            run_cmd = 'cd '+_f+' && /bin/csh '+comp_cmd+' '+cmd_line_args_dict['compile_repeat_number']+' && /bin/csh '+sim_cmd
        for _c, _v in cmd_line_args_dict['enable_custom_switch_valuable'].items():
            var_cmd += 'export '+_c+'='+_v+' && ' #FIXME: bash? csh?
        lsf_cmd += 'bsub '+' '.join(cfg_file_items_dict['bsub_opt'])+' '
        lsf_cmd += ' '.join(cmd_line_args_dict['extra_lsf_options'])+' '
        lsf_cmd += '-J '+cmd_line_args_dict['lsf_job_group_name']+' '
        if cmd_line_args_dict['lsf_hosts']: lsf_cmd += '-m ' + '-m '.join(cmd_line_args_dict['lsf_hosts'])+' '
        if cmd_line_args_dict['interactivelsf']: lsf_cmd += '-I '
        else: lsf_cmd += '-K ' #-K: submits a batch job and waits for the job to complete, FIXME
        full_cmd = (var_cmd+lsf_cmd+'\"'+run_cmd+'\"') if cmd_line_args_dict['lsf'] else var_cmd+run_cmd
        if cmd_line_args_dict['compile_only']: logs_to_be_parsed.append(_f+'/comp.log')
        else:
            logs_to_be_parsed.append(_f+'/latest_sim.log')
            for i in cfg_file_items_dict['other_sim_log_files']:
                if i.startswith('/') or i.startswith('$'): logs_to_be_parsed.append(i)
                else: logs_to_be_parsed.append(_f+'/'+i)
        generated_folders_info_dict[_f]['shellcmd'] = full_cmd
        generated_folders_info_dict[_f]['logs'] = logs_to_be_parsed
        thread_list.append(threading.Thread(target=f_run_and_parse, args=(generated_folders_info_dict[_f]['test'], generated_folders_info_dict[_f]['seed'], _f, full_cmd, logs_to_be_parsed, cmd_line_args_dict['interactivelsf'])))
    for t in thread_list: t.start()
    for t in thread_list: t.join()

def f_print_msg_periodic():
    global pool_sema
    pool_sema.acquire()
    done_flag = False
    finished_run_cnt = 0
    if regression_flag:
        finished_run_cnt = error_runs_in_regression+warn_runs_in_regression+pass_runs_in_regression
        while finished_run_cnt<total_runs_in_regression:
            print('Running. Finished/Total = '+str(finished_run_cnt)+'/'+str(total_runs_in_regression)+' @ '+datetime.datetime.now().strftime('%m.%d %H:%M:%S'))
            print('\t\tPass: '+str(pass_runs_in_regression)+', Warn: '+str(warn_runs_in_regression)+', Error: '+str(error_runs_in_regression)+', Still running: '+str(total_runs_in_regression-finished_run_cnt))
            if period_print_msg_interval > 0:
                for t in range(period_print_msg_interval):
                    time.sleep(1) #seconds
                    finished_run_cnt = error_runs_in_regression+warn_runs_in_regression+pass_runs_in_regression
                    if finished_run_cnt >= total_runs_in_regression:
                        done_flag = True
                        break #quit for loop of t
                if done_flag: break #quit while loop and f_print_msg_periodic
            else: time.sleep(1) #seconds
            finished_run_cnt = error_runs_in_regression+warn_runs_in_regression+pass_runs_in_regression
        print('--*-- All jobs('+str(total_runs_in_regression)+') done! --*--')
        print('\t\tPass: '+str(pass_runs_in_regression)+', Warn: '+str(warn_runs_in_regression)+', Error: '+str(error_runs_in_regression))
    else: pass
    pool_sema.release()

def f_run_and_parse(test, seed, folder, cmd, logs, interactive=True):
    global error_runs_in_regression
    global warn_runs_in_regression
    global pass_runs_in_regression
    global running_runs_in_regression
    global pool_sema
    global generated_folders_info_dict
    global period_print_msg_interval
    pool_sema.acquire()
    return_value = ''
    return_list = []
    running_runs_in_regression += 1
    if regression_flag: print('Start running a job in folder '+folder+' , ('+str(total_runs_in_regression-running_runs_in_regression)+' jobs in waiting list)')
    generated_folders_info_dict[folder]['simstart'] = datetime.datetime.now() #the time before running
    if interactive: return_value = os.system(cmd) #return return value
    else: return_value = os.system('('+cmd+') >& /dev/null') #do not print simulation screen log in this condition
    generated_folders_info_dict[folder]['simend'] = datetime.datetime.now() #the time after running
    generated_folders_info_dict[folder]['simwindow'] = \
	str(generated_folders_info_dict[folder]['simend']-generated_folders_info_dict[folder]['simstart'])
    return_list = f_parse_log(logs, folder) #comp.log is parsed when '-compile_only', or else, simulation logs are parsed
    generated_folders_info_dict[folder]['logparsedtime'] = datetime.datetime.now() #the time after parsing simulation log
    if return_list[0]:
        generated_folders_info_dict[folder]['result'] = '_ERROR_'
        error_runs_in_regression += 1
        if single_simulation_flag:
            f_result_print('Fail', 'red')
            f_colorful_print(return_list[2], 'red')
            print()
            f_colorful_print(return_list[0], 'red')
            print()
        if regression_flag:
            f_colorful_print('Error: '+folder+' Seed: '+str(seed), 'red')
            print()
    elif return_list[1]:
        generated_folders_info_dict[folder]['result'] = '_WARN_'
        warn_runs_in_regression += 1
        if single_simulation_flag:
            f_result_print('Warn', 'yellow')
            f_colorful_print(return_list[2], 'yellow')
            print()
            f_colorful_print(return_list[1], 'yellow')
            print()
        if regression_flag:
            f_colorful_print('Warn: '+folder+' Seed: '+str(seed), 'yellow')
            print()
    else:
        generated_folders_info_dict[folder]['result'] = '_PASS_'
        pass_runs_in_regression += 1
        if single_simulation_flag:
            f_result_print('Pass', 'green')
        if regression_flag:
            f_colorful_print('Pass: '+folder+' Seed: '+str(seed), 'green')
            print()
    if cmd_line_args_dict['compile_only']:
        print('!! Compile Only !!')
        print()
    if (error_runs_in_regression+warn_runs_in_regression+pass_runs_in_regression) >= total_runs_in_regression: period_print_msg_interval = 1 #shorten message print interval
    f_gen_result_files(folder)
    if single_simulation_flag:
        print('Test: ' + test + ' Seed: ' + str(seed))
    pool_sema.release()

def f_gen_result_files(key_in_info_dict): #generate _ERROR_, _WARN_, _PASS_, and _error.lst, _warn.lst, _pass.lst
    global generated_folders_info_dict
    result = generated_folders_info_dict[key_in_info_dict]['result']
    parent = generated_folders_info_dict[key_in_info_dict]['parent']
    seed = generated_folders_info_dict[key_in_info_dict]['seed']
    script = generated_folders_info_dict[key_in_info_dict]['script']
    if not generated_folders_info_dict[key_in_info_dict]['done']:
        os.system('\\touch '+key_in_info_dict+'/'+result)
        if regression_flag:
            if result=='_ERROR_': os.system('\\echo \"'+script+'\" >> '+parent+'/_error.lst')
            if result=='_WARN_': os.system('\\echo \"'+script+'\" >> '+parent+'/_warn.lst')
            if result=='_PASS_': os.system('\\echo \"'+script+'\" >> '+parent+'/_pass.lst')
        os.system('\\echo \"'+script+'\" > '+key_in_info_dict+'/_cmd_line')
        generated_folders_info_dict[key_in_info_dict]['done'] = True

def f_check_unfinished_items():
    unfinished_item_cnt = 0
    for i in generated_folders_info_dict.keys():
        if not generated_folders_info_dict[i]['done']: unfinished_item_cnt += 1
    if unfinished_item_cnt:
        f_colorful_print('Unfinished item: '+str(unfinished_item_cnt), 'red')
        print()
    for i in generated_folders_info_dict.keys():
        if not generated_folders_info_dict[i]['done']: print('\t\t'+i)

def f_parse_log(logs, simfolder): #return first error, first warning and file name
    return_list = ['', '', '']
    for _l in logs:
        if _l.startswith('$run_dir'):
            _l = _l.replace('$run_dir', simfolder)
        if not os.path.exists(_l): return ['File Not Exist','',_l]
        print('Paring '+_l+' ...')
        with open(_l, 'r') as f:
            got_error = False
            got_warning = False
            for _line in f:
                ignore_warning = False
                ignore_error = False
                _line = str(_line).replace('\n', '').replace('\t', '').strip()
                if len(_line) == 0: continue
                if _line == '--- UVM Report Summary ---': break
                for _w in cfg_file_items_dict['ignore_warn_str']:
                    if _w in _line:
                        ignore_warning = True
                        break
                if not ignore_warning:
                    for _w in cfg_file_items_dict['warn_str']:
                        if _w in _line:
                            got_warning = True
                            return_list = ['', _line, _l]
                            break
                for _e in cfg_file_items_dict['ignore_err_str']:
                    if _e in _line:
                        ignore_error = True
                        break
                if not ignore_error:
                    for _e in cfg_file_items_dict['err_str']:
                        if _e in _line:
                            got_error = True
                            break
                if got_error: return [_line, '', _l]
    return return_list

def f_ctrl_c_handle(signal, frame):
    global ctrl_c_times
    global pre_ctrl_c_time
    global jobs_were_killed_by_two_ctrl_c
    global period_print_msg_interval
    if ((datetime.datetime.now()-pre_ctrl_c_time).seconds > 5) and (not jobs_were_killed_by_two_ctrl_c):
        ctrl_c_times = 0
    ctrl_c_times += 1
    f_colorful_print(str(ctrl_c_times)+' time(s)', 'Red')
    print()
    if ctrl_c_times >= 2:
        jobs_were_killed_by_two_ctrl_c = True
        period_print_msg_interval = 1 #shorten message print interval
        if ctrl_c_times == 2:
            f_colorful_print('kill jobs', 'red')
            print()
        else:
            f_colorful_print('killing jobs', 'red')
            print()
        if cmd_line_args_dict['lsf']:
            out = os.system('bkill -J '+cmd_line_args_dict['lsf_job_group_name']) #FIXME: is bkill?
        else:
            f_colorful_print('Not running with LSF, how to kill?', 'red') #TODO
            print()
    if ctrl_c_times == 10:
        f_colorful_print('Press 10 times Ctrl+C, script quits immediately.', 'red')
        print()
        out = os.system('bkill -J '+cmd_line_args_dict['lsf_job_group_name']) #FIXME: is bkill?
        sys.exit(2)
    if ctrl_c_times > 10:
        f_colorful_print('More than 10 Ctrl+C, waiting for script quits.', 'red')
    pre_ctrl_c_time = datetime.datetime.now()

def f_colorful_print(word, color='cyan'):
    colors = {
        'black':        '30',
        'red':          '31',
        'green':        '32',
        'yellow':       '33',
        'blue':         '34',
        'magenta':      '35',
        'cyan':         '36',
        'white':        '37'
    }
    color_code = colors.get(color.lower(), '37')
    print('\033[{}m{}\033[0m'.format(color_code, word), end=' '*3)

def f_result_print(word, color):
    characters = {
        'P': ['##### ',
              '#    #',
              '#    #',
              '##### ',
              '#     ',
              '#     ',
              '#     '],
        'A': ['   #   ',
              '  # #  ',
              ' #   # ',
              '#######',
              '#     #',
              '#     #',
              '#     #'],
        'S': [' ##### ',
              '#     #',
              '#      ',
              ' ##### ',
              '      #',
              '#     #',
              ' ##### '],
        'W': ['#     #',
              '#     #',
              '#     #',
              '#     #',
              '#  #  #',
              '# # # #',
              '#     #'],
        'R': ['###### ',
              '#     #',
              '#     #',
              '###### ',
              '#   #  ',
              '#    # ',
              '#     #'],
        'N': ['#     #',
              '##    #',
              '# #   #',
              '#  #  #',
              '#   # #',
              '#    ##',
              '#     #'],
        'F': ['#######',
              '#      ',
              '#      ',
              '###### ',
              '#      ',
              '#      ',
              '#      '],
        'I': ['  ###  ',
              '   #   ',
              '   #   ',
              '   #   ',
              '   #   ',
              '   #   ',
              '  ###  '],
        'L': ['#      ',
              '#      ',
              '#      ',
              '#      ',
              '#      ',
              '#      ',
              '#######']
    }
    for _i in range(7):
        _art = ''
        for _c in word:
            _art += ' '+characters[_c.upper()][_i]+' '
        f_colorful_print(_art, color)
        print('')

def f_timestamp_print_in_sim(output_dir): #called by f_gen_eda_wrapper_scripts
    date_c_string = []
    date_c_string.append('#include <time.h>')
    date_c_string.append('long int date() {')
    date_c_string.append('\ttime_t t = time(NULL);')
    date_c_string.append('\tstruct tm tm = *localtime(&t);')
    return_date_string = ''
    return_date_string += '(tm.tm_mon+1)*(1e12)'
    return_date_string += '+(tm.tm_mday)*(1e9)'
    return_date_string += '+(tm.tm_hour)*(1e6)'
    return_date_string += '+(tm.tm_min)*(1e3)'
    return_date_string += '+(tm.tm_sec)*(1e0)'
    date_c_string.append('\treturn '+return_date_string+';')
    date_c_string.append('}')
    automsg_sv_string = []
    automsg_sv_string.append('bind `_TB_TOP_ automsg u_atm();')
    automsg_sv_string.append('import \"DPI-C\" function longint date();')
    automsg_sv_string.append('module automsg;')
    automsg_sv_string.append('\tinitial print_msg();')
    automsg_sv_string.append('\tinitial forever begin #5ms; print_msg(); end')
    automsg_sv_string.append('\tfinal print_msg();')
    automsg_sv_string.append('\tfunction void print_msg();')
    automsg_sv_string.append('\t\t$display(\"%m:%0t:%s\", $time, `_CMD_LINE_);')
    automsg_sv_string.append('\t\t$display(\"%s:%s\", `_PRJ_NAME_, `_PRJ_ROOT_);')
    automsg_sv_string.append('\t\t$display(\"%s\", `_RUN_DIR_);')
    automsg_sv_string.append('\t\tprint_date(date());')
    automsg_sv_string.append('\tendfunction: print_msg')
    automsg_sv_string.append('\tfunction void print_date(longint date_longint);')
    automsg_sv_string.append('\t\tint mon, mday, hour, min, sec;')
    automsg_sv_string.append('\t\tmon = date_longint/1e12;')
    automsg_sv_string.append('\t\tmday = (date_longint-mon*1e12)/1e9;')
    automsg_sv_string.append('\t\thour = (date_longint-mon*1e12-mday*1e9)/1e6;')
    automsg_sv_string.append('\t\tmin = (date_longint-mon*1e12-mday*1e9-hour*1e6)/1e3;')
    automsg_sv_string.append('\t\tsec = (date_longint-mon*1e12-mday*1e9-hour*1e6-min*1e3)/1e0;')
    automsg_sv_string.append('\t\t$display(\"%01d.%02d %02d:%02d:%02d\", mon, mday, hour, min ,sec);')
    automsg_sv_string.append('\tendfunction: print_date')
    automsg_sv_string.append('endmodule //automsg')
    with open(output_dir+'/date.c', 'w+') as f: f.write('\n'.join(date_c_string))
    with open(output_dir+'/automsg.sv', 'w+') as f: f.write('\n'.join(automsg_sv_string))

def main():
    global thread_list
    global pool_sema
    signal.signal(signal.SIGINT, f_ctrl_c_handle)
    f_init_dicts()
    f_help_doc()
    f_parse_cmd_line(sys.argv)
    if os.path.isfile(cmd_line_args_dict['sim_setup']): f_parse_config_file(cmd_line_args_dict['sim_setup'])
    elif cmd_line_args_dict['block']:
        _path_of_cfg = f_find_file(env_prj_root, cmd_line_args_dict['dv_folder']+'/sim.setup', cmd_line_args_dict['block']+'/'+cmd_line_args_dict['dv_folder'])
        f_parse_config_file(_path_of_cfg)
    else:
        _path_of_cfg = f_find_file(env_prj_root, cmd_line_args_dict['dv_folder']+'/sim.setup', env_prj_root+'/'+cmd_line_args_dict['dv_folder'])
        f_parse_config_file(_path_of_cfg)
    if localdv_flag:
        _path_of_sub_cfg = ''
    elif single_simulation_flag:
        _path_of_sub_cfg = ''
        if cmd_line_args_dict['block']:
            _path_of_sub_cfg = f_find_file(env_prj_root, cmd_line_args_dict['test'][0]+'/sim.setup', cmd_line_args_dict['block']+'/'+cmd_line_args_dict['dv_folder']+'/tests')
        else:
            _path_of_sub_cfg = f_find_file(env_prj_root+'/'+cmd_line_args_dict['dv_folder']+'/tests', cmd_line_args_dict['test'][0]+'/sim.setup')
        if _path_of_sub_cfg: f_parse_config_file(_path_of_sub_cfg)
    pool_sema = threading.BoundedSemaphore(cmd_line_args_dict['max_run_in_parallel']+1)
    thread_list.append(threading.Thread(target=f_print_msg_periodic, args=[]))
    f_gen_folders()
    if cmd_line_args_dict['gen_scripts_only']:
        f_colorful_print('Scripts generated.', 'green')
        print()
    else: f_start_running()
    print('')
    print(sys.argv)
    print('\n'.join(global_info_msg))
    if regression_flag and not cmd_line_args_dict['gen_scripts_only']:
        f_check_unfinished_items()
        f_plot_curve()
    with open(sim_base_dir+'/README', 'a+') as f:
        if cmd_line_args_dict['single_in_regr']: f.write('\n\n//==== generated_folders_info_dict single_in_regr ====\n')
        else: f.write('\n\n//==== generated_folders_info_dict ====\n')
        f.write(str(generated_folders_info_dict))
    end_time = datetime.datetime.now() #update by the end of the script
    print('\n*'+sys.argv[0]+' runs from '+str(start_time)+' to '+str(end_time)+', total duration:'+str(end_time-start_time))

if __name__ == "__main__":
    main()
