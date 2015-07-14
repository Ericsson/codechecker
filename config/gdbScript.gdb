set follow-fork-mode child
set print pretty on
set print array on
set print demangle on
run
where
backtrace full
frame
info args
info locals
show print demangle
list
quit

