setenv PRJ_NAME example
#setenv PRJ_ROOT ~/example
setenv PRJ_ROOT `realpath $argv[1]`
setenv DV_ROOT $PRJ_ROOT/dv
setenv SIM_ROOT $PRJ_ROOT/sim
