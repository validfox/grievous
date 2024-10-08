# Grievous
    General Grievous :)

    An EDA simulator wrapper script of Cadence Xcelium, Synopsys VCS, etc.
    Use one line command to call different digital simulators in short.
    An example is to start a simulation with a command like 'python3 grievous.py -t test0'.

    Follow MIT license.

    Nowadays, in digital design and verification team of an integrated circuit (IC) company,
        a common script of invoking different simulators is used normally.
    The script is based on perl, python or makefile in different companies.

    The scirpt in this repo is programmed by python3.
    With the help of some configuration text files and global variables,
        the script creates simulation folders, compile scripts, and simulate scripts,
        then runs them automatically.
    Different engineers are easily to share and debug simulation results in the team,
        and easily to reproduce a failed simulation if they are using the same script.

    Both single simulation and regression are supported.
    Coverage is also collected in need,
        and the curve of coverage percentage of daily regression is generated by calling gnuplot.

    Support to sumbit jobs to LSF system or current host.

    Support UVM testbench and verilog-only testbench.
    For verification engineers, an UVM based simulation environment is easily to be build.
    For design engineers who are not familiar with UVM,
        a verilog or systemverilog based simulation environment is also supported.

    TBA

# Usage, arguments
| Argument | Description |
| - | - |
| --debug | Print more message. `For debug only.` |
| -h | Print help message of the script. `Without start a simulation.` |
| -t [test_name] | Specify the name of a test. `It's used to find a file which name is [test_name].sv, and the [test_name] is passed to simulatior as +UVM_TESTNAME=[test_name]. So, make sure the file name and uvm_test name are same with [test_name]. Specify more than one test will start a regression. For example, '-t test0 -t test1' is workable.` |
| -r [regression_list_file] | Sepcify a file of regression test list. `See an example file in below.` |
| -g [regression_group_name] | Sepcify a group name in regression list file. `More than one group can be selected. For example, using '-g A -g B' in the same command line will select two groups in the list.` |
| -uvm | Enable the compilation of UVM packages. `By default, UVM packages are compiled.` |
| -nouvm | Disable the compilation of UVM packages. |
| -c | Clean existing simulation folder. `Without this arguments, the compile stage keeps incremental compilation if simulation folder is reused.` |
| -s [seed] | Specify the seed of a simulation. `The seed will passed to simulators. If seed isn't specified, the script generates a random seed in background.` |
| -w [wave_type] | Dump signals to waveform files. `[wave_type] can be ommitted, the default waveform type of Cadence Xceilum is .shm, and the default type of Synopsys VCS is fsdb. Wave type can also be specified in command line, it supports [-w shm, -w vcd, -w fsdb, -w vpd] for now. The signals and hierachies are specified in a user-defined file.` |
| -wall [wave_type] | Dump all signals in all hierachy into waveform files. |
| -atm | Print extra message in simulation. `Extra message includs folder name, command and system time. It's useful infomation when the simulation runs for days, weeks, or even months.` |
| -noatm | Disable extra message printed. `Note that the extra message is enabled by default in a single simulation.` |
| -input [tcl_file] | Specify a tcl file and pass it to simulator. `Pass to Cadence Xcelium: 'xrun -input [tcl_file] ...'` |
| -b [block_name] | Specify block name for block level verification. `Do NOT use this argument if it's a TOP level verification. The [block_name] should be the folder name of a block level design.` |
| -dv[\d*] | Means -dv, -dv0, -dv1, or -dv2..., specify another dv folder as default. `If the dv folder name is 'dv', -dv can be ommitted.` |
| -localdv[\d*] | Means -localdv, -localdv0, -localdv1, or -localdv2..., specify another dv folder as default. `LocalDV is a temprary DV environment, which is assumed to be a non-UVM environment which is used by design engineers.` |
| -rtl | Pre simulation with RTL only. `By default, it's a pre simulation.` |
| -gate | Post simulation with gate level netlist. |
| -fpga | Simualtion for FPGA use. |
| -cosim | `Not support yet.` |
| -fault | `Not support yet.` |
| -tfile [tfile] | Specify timing file '.tfile'. `Multiple tfile files can be specified by calling '-tfile [tfile]' multiple times.` |
| -lsf | Calling 'bsub'. `By default, bsub is called. But if LSF is not installed, use '-nolsf' in command line.` |
| -nolsf | Do not call 'bsub'. |
| -interactivelsf | Calling 'bsub -I' for interactive mode of LSF. |
| -nointeractivelsf | Do not use '-I' of bsub command. `By default, a single simulation use 'bsub -I ...' to submit job to LSF.` |
| -jname [job_queue_name] | Specify job queue name of bjobs. |
| -rcn [number] | Specify compile repeat times. `If compile fails, the script re-compiles database, by default, by 3 times.` |
| -sim_root [folder_path] | Specify a folder that all the simulation folders are created under that folder. `By default, the folder is defined in global variable 'SIM_ROOT'.` |
| -d [folder_path] | Specify a folder to run simulation, instead of creating one automatically. |
| -repeat [number] | Run a simulation or regression for [number] times. `For example, to run a test for 10 times, use 'python3 grievous.py -t test0 -repeat 10'.` |
| -append [string] | For generated folder, its name is the test name. In order to distinguish the test from another run, append something to the folder name. `For example: [test_name]_[string] is the new name of simulation folder.` |
| -setup [another_config_file] | Specify another configuration file, instead of using the default one 'sim.setup'. |
| -max [number] | Specify the maxium number of parallel running jobs in regression. `By default, the max number is 10. It's useful in regression when computer resoure is limited.` |
| -qc [number] | Simulation quits when the count of error is larger than [number]. |
| -m [host_name] | Specify the host or hosts where the jobs are submitted in LSF. |
| -inf | `Not support yet.` |
| -ext_lsf_opt "string" | Pass some options to bsub from command line. `Users can also specify options to bsub from configuration files.` |
| -ext_comp_opt "string" | Pass some options to simulator at compilation stage. `Users can also specify options to bsub from configuration files.` |
| -ext_sim_opt "string" | Pass some options to simulator at simulation stage. `Users can also specify options to bsub from configuration files.` |
| -ext_dbg_opt "string" | Pass some options to Cadence Simvision, Synopsys Verdi. `Users can also specify options to bsub from configuration files.` |
| -ext_opt "string" | Pass some options to simulators, at both compilation and simulation stages. `Users can also specify options to bsub from configuration files.` |
| -co | Compile but not simulate. |
| -gs | Generate simulation folder and scripts, but do NOT start compile and simulate. |
| -cov | Enable coverage collection. |
| -cm | For regression, merge the coverage of every tests together. |
| -nocov | Disable coverage collection, higher priority than '-cov'. |
| -refine [refine_file_name] | Specify refine file used in coverage collection and merge. |
| -gui | Run simulation in gui mode. |
| -nc | Use Cadence Xcelium as the simulator. `The default simulator is set to Xcelium.` |
| -vcs | Use Synopsys VCS as the simulator. |
| -simtmp | For Cadence Xcelium, a user-defined folder can be set as simulation intermedia folder. `See more details in user guide of Xcelium.` |
| +[options] | Any options with leading '+' will be passed to simulator directly. |
| -[custom_switch] [value] | Enable a custom switch, and give a value of it. `[value] is not necessary.` |
| --[custom_switch] | Disable a custom switch. `If a custom swithc is default on in configuration file. It's also can be disabled from command line.` |

    TBA

# Global variables

    # project.cshrc
    setenv PRJ_NAME [project_name]
    setenv PRJ_ROOT `realpath $argv[1]`
    setenv DV_ROOT $PRJ_ROOT/dv
    setenv SIM_ROOT $PRJ_ROOT/sim

# Configuration files
    The default name of configuration file is 'sim.setup'.
    For block level or top level verification, a default 'sim.setup' should be created by user:
        $DESIGN_ROOT/[block_name]/dv/sim.setup
        $DV_ROOT/sim.setup
    
    In configuration files, each line is a key-value pair,
        which guides the script to run simulation.
    For example, 'DESIGN_TOP: example' is used to tell the script the top module name.

| KeyWord | Value |
| - | - |
| SOURCE_CFG | Specify a child configuration file. `In order to reuse some common settings.` |
| CUSTOM_SWITCH | Add a new custom switch which can be used in command line to enable to disable something. `See relate chapter in this README file.` |
| DESIGN_TOP | Specify the module name of top design. `Which is the DUT in the context.` |
| TB_TOP | Specify the module name of testbench. |
| INC_DIR | Include folders. `Pass to simulator '+incdir+[path]'` |
| DESIGN_FILES | Specify the file-list file or design file. |
| DV_FILES | Specify the file-list file or dv file. |
| LIB_FILES | Specify library file-list file or single files. |
| MODEL_FILES | Specify models or modle list. |
| TIME_SCALE | Specify time-scale of simulation. |
| UVM_TIMEOUT | Set uvm_timeout time. |
| MAX_QUIT_COUNT | Set max_quit_count in simulation. |
| COMPILE_REPEAT_NUMBERS | Repeat times when compile fails. |
| BLK_ROOT | Root folder of block. `Useful in block level verification only.` |
| BLK_DESIGN_ROOT | Root folder of block design. `Useful in block level verification only.` |
| BLK_DV_ROOT | Root foloder of block DV environment. `Useful in block level verification only.` |
| TCL_FILES | Pass tcl files to simulator using '-input' option of simulator. |
| TFILES | Pass tfiles to simulator in gate level simulation. |
| BSUB_OPT | Options passed to 'bsub' command. |
| EXT_COMP_OPT | Options passed to simulator in compilation stage. |
| EXT_SIM_OPT | Options passed to simulator in simulation stage. |
| EXT_OPT | Options passed to simulator in both compilation and simulation stages. |
| EXT_DBG_OPT | Options passed to Cadence Simvision and Synopsys Verdi. |
| PRE_COMP_CMD | Some commands executed before compilation starts. |
| POST_COMP_CMD | Some commands executed after compilation is done, but before simulation starts. |
| PRE_SIM_CMD | Some commands executed before simulation starts, but after compilation is done. `Such like to move data file to simulation folder.` |
| POST_SIM_CMD | Some commands executed after simulation is done. `Such like some post text file processing.` |
| COV_TYPE | Coverage type for coverage collection. |
| COV_FILES | Specify setting files for coverage collection. |
| COV_DUT | Specify one or more DUTs for collecting coverage. |
| COV_REFINE_FILES | Specify refine files for coverage collections and merge. |
| WARN_STR | User-define string which is used to parse log files to treated as warning message. |
| IGNORE_WARN_STR | User-define string which is used to parse log files to treated as NOT warning message. |
| ERR_STR | User-define string which is used to parse log files to treated as error message. |
| IGNORE_ERR_STR | User-define string which is used to parse log files to treated as NOT error message. |
| OTHER_SIM_LOG_FILES | Sepcify some other log files which will be parsed by the scripts. |

## Example of configuration

    DESIGN_TOP: example
    TB_TOP: tb_top

    DESIGN_FILES: -f design.f
    DV_FILES: -f dv.f

    CUSTOM_SWITCH: cs0, default:ON, append:ON
    CUSTOM_SWITCH: cs1, default:ON, append:OFF

    cs0_PRE_COMP_CMD: echo "cs0_pre_comp_cmd"
    !cs0_PRE_COMP_CMD: echo "not cs0_pre_comp_cmd"
    cs0_POST_COMP_CMD: echo "cs0_pre_comp_cmd"
    !cs0_POST_COMP_CMD: echo "not cs0_pre_comp_cmd"

    cs0_PRE_COMP_CMD: echo "cs0_pre_comp_cmd 1"
    !cs0_PRE_COMP_CMD: echo "not cs0_pre_comp_cmd 1"
    cs0_POST_COMP_CMD: echo "cs0_pre_comp_cmd 1"
    !cs0_POST_COMP_CMD: echo "not cs0_pre_comp_cmd 1"

    cs0_PRE_SIM_CMD: echo "cs0_pre_sim_cmd"
    !cs0_PRE_SIM_CMD: echo "not cs0_pre_sim_cmd"
    cs0_POST_SIM_CMD: echo "cs0_pre_sim_cmd"
    !cs0_POST_SIM_CMD: echo "not cs0_pre_sim_cmd"

    cs0_cs1_PRE_COMP_CMD: echo "cs0_cs1_PRE_COMP_CMD"
    cs0_!cs1_PRE_COMP_CMD: echo "cs0_!cs1_PRE_COMP_CMD"
    !cs0_!cs1_PRE_COMP_CMD: echo "!cs0_!cs1_PRE_COMP_CMD"
    !cs0_cs1_PRE_COMP_CMD: echo "!cs0_cs1_PRE_COMP_CMD"

## Custom switch
    To make the script more robust,
        users can define new switches which can be used in command line.
    Custom switch is added in configuration files as the value of 'CUSTOM_SWITCH' keyword.
    
    The line
    CUSTOM_SWITCH: cs0, default:ON, append:ON
    means, a custom switch 'cs0' is added, it's enabled by default,
        and it will append '_cs0' to the simulation folder name.

    Use regexp to have more flexbility to keywords in configuration files.

    For example, refer to the above example of configuration file,
        cs0 and cs1 are user added custom switches.
    cs0_ and cs1_ are added to ANY keywords in configuration files,
        some have '!' in front of custom switch which means negtive selections.
    
    To enable cs0 custom swith in command line, use '-cs0'
        > python3 grievous.py -t test0 -cs0
        as cs0 is enabled by default in configuration file, -cs0 can be ommitted.
    
    To disable cs0 custom switch in command line, use '--cs0'
        > python3 grievous.py -t test0 --cs0
    
    To enable cs0, but disable cs1 in command line
        > python3 grievous.py -t test0 -cs0 --cs1
    
    To disable cs0, but enable cs1 in command line
        > python3 grievous.py -t test0 --cs0 -cs1
    
    The line
    cs0_!cs1_PRE_COMP_CMD: echo "cs0_!cs1_PRE_COMP_CMD"
    is only functional when cs0 is enable and cs1 is disable,
    aka 'python3 grievous.py -cs0 --cs1 ...' or 'python3 grievous.py --cs1 ...'.
        Note: cs0 is default on, so -cs0 is not necessary in this context.

# Regression list file example
    # full.lst
    test0 : A=1 B=2 GroupX=3
    test1 -seed 2 : A=1
    test3 -nocov : B=2

## Usage
    Group name can be any character or word.

    '-seed 2' and '-nocov' are options for test1 and test3, respectively, not affect test0.

    'python3 grievous.py -r full.lst -g A -g B -cov -cm' will run a regression, in which, test0 run 3 times,
        test1 run once but with 2 as seed,
        and test3 run twice.
        Only collect the coverage of test0 and test1, as '-nocov' is used in the line of test3.
    
    Note: Failed tests will not be collected coverage.
    Note: For daily regression, gnuplot is invoked to plot curve of coverage info.

# Features by now and in future

    TBA

# Contact
xeroncn+validfox.python3 grievous.py@gmail.com
