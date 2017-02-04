#include <stdio.h>
#include <stdlib.h>
#include "i2c.h"
#include "pca9548.h"

void pca9548_select(int channel)
{
    printf("%s: channel=%d\n", __func__, channel);

    i2c_start(0);
    if(!i2c_write(0, (0x74 << 1))) {
        puts("PCA9548 failed to ack write address");
        abort();
    }
    if(!i2c_write(0, 1 << channel)) {
        puts("PCA9548 failed to ack control word");
        abort();
    }
    i2c_stop(0);
}

int pca9548_readback()
{
    i2c_start(0);
    if(!i2c_write(0, (0x74 << 1) | 1)) {
        puts("PCA9548 failed to ack read address");
        abort();
    }
    int channel = i2c_read(0, 0);
    i2c_stop(0);

    printf("%s: channel=%d\n", __func__, channel);

    return channel;
}
