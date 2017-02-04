#include <stdio.h>
#include <stdlib.h>
#include <generated/csr.h>
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
    printf("ok\n");

    uint8_t skew = 0;
    while(1) {
        si5324_set_skew(skew);
        printf("skew set to %d\n", (int8_t)skew);
        skew = (skew + 1) % 8;

        timer0_en_write(0);
        timer0_load_write(10*CONFIG_CLOCK_FREQUENCY); // 10s
        timer0_reload_write(0);
        timer0_en_write(1);

        timer0_update_value_write(1);
        while(timer0_value_read() != 0)
            timer0_update_value_write(1);
    }
}
