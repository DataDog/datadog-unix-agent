#include <stdio.h>
#include <sys/time.h>

int main() {
  timebasestruct_t timebase;
  unsigned long long int *ticks, secs;

  read_wall_time(&timebase, TIMEBASE_SZ);
  ticks = (unsigned long long int*) &timebase.tb_high;
  secs = *ticks / 512000000; // There are 512 ticks per microsecond
  printf("%llu\n", secs);
}


