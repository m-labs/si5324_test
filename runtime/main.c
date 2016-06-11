#include <stdio.h>
#include <stdlib.h>
#include <irq.h>
#include <uart.h>
#include "i2c.h"
#include "pca9548.h"
#include "si5324.h"

int main(void)
{
    irq_setmask(0);
    irq_setie(1);
    uart_init();

    puts("Si5324 runtime built "__DATE__" "__TIME__"\n");

    i2c_init(0);
    pca9548_select(7);
    pca9548_readback();

    si5324_init_125MHz(4);
    printf("waiting for ");
    printf("xtal... ");
    while(!si5324_has_xtal());
    printf("input... ");
    while(!si5324_has_input());
    printf("PLL lock... ");
    while(!si5324_locked());
    printf("actviation... ");
    while(!si5324_active());
    printf("ok\n");

    while(1);
}
