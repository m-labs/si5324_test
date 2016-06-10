#include <stdio.h>
#include <stdlib.h>
#include <irq.h>
#include <uart.h>
#include "i2c.h"
#include "pca9548.h"
#include "si5324.h"

void fail(const char *reason);
void fail(const char *reason)
{
    puts(reason);
    abort();
}

int main(void)
{
    irq_setmask(0);
    irq_setie(1);
    uart_init();

    puts("Si5324 runtime built "__DATE__" "__TIME__"\n");

    i2c_init(0);
    pca9548_select(7);
    si5324_reset();

    while(1);
}
