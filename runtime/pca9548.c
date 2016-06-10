#include <stdio.h>
#include <stdlib.h>
#include "i2c.h"
#include "pca9548.h"

void pca9548_select(int channel)
{
    printf("%s: channel=%d\n", __func__, channel);
    i2c_start(0);
    if(!i2c_write(0, 0xe8)) {
        puts("PCA9548 failed to ack address");
        abort();
    }
    if(!i2c_write(0, 1 << channel)) {
        puts("PCA9548 failed to ack control word");
        abort();
    }
    i2c_stop(0);
}
