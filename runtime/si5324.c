#include <stdio.h>
#include <stdlib.h>
#include <generated/csr.h>
#include "i2c.h"
#include "si5324.h"

void si5324_reset()
{
    printf("%s\n", __func__);

    timer0_en_write(0);
    timer0_load_write(CONFIG_CLOCK_FREQUENCY/100); // 10ms
    timer0_reload_write(0);
    timer0_en_write(1);

    si5324_rst_n_out_write(0);

    timer0_update_value_write(1);
    while(timer0_value_read() != 0)
        timer0_update_value_write(1);

    si5324_rst_n_out_write(1);
}
