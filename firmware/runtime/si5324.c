#include <stdio.h>
#include <stdlib.h>
#include <generated/csr.h>
#include "i2c.h"
#include "si5324.h"

void si5324_reset()
{
    timer0_en_write(0);
    timer0_load_write(CONFIG_CLOCK_FREQUENCY/50); // 20ms
    timer0_reload_write(0);
    timer0_en_write(1);

    si5324_rst_n_out_write(0);

    timer0_update_value_write(1);
    while(timer0_value_read() != 0)
        timer0_update_value_write(1);

    si5324_rst_n_out_write(1);

    timer0_update_value_write(1);
    while(timer0_value_read() != 0)
        timer0_update_value_write(1);
}

#define ADDRESS 0x68

void si5324_write(uint8_t reg, uint8_t val)
{
    // printf("%s: [%d]=0x%02x\n", __func__, reg, val);

    i2c_start(0);
    if(!i2c_write(0, (ADDRESS << 1))) {
        puts("Si5324 failed to ack write address");
        abort();
    }
    if(!i2c_write(0, reg)) {
        puts("Si5324 failed to ack register");
        abort();
    }
    if(!i2c_write(0, val)) {
        puts("Si5324 failed to ack value");
        abort();
    }
    i2c_stop(0);
}

uint8_t si5324_read(uint8_t reg)
{
    i2c_start(0);
    if(!i2c_write(0, (ADDRESS << 1))) {
        puts("Si5324 failed to ack write address");
        abort();
    }
    if(!i2c_write(0, reg)) {
        puts("Si5324 failed to ack register");
        abort();
    }
    i2c_restart(0);
    if(!i2c_write(0, (ADDRESS << 1) | 1)) {
        puts("Si5324 failed to ack read address");
        abort();
    }
    uint8_t val = i2c_read(0, 0);
    i2c_stop(0);

    // printf("%s: [%d]=0x%02x\n", __func__, reg, val);

    return val;
}

uint16_t si5324_ident()
{
    return (si5324_read(134) << 8) | si5324_read(135);
}

void si5324_program(int bwsel)
{
    si5324_reset();

    if(si5324_ident() != 0x0182) {
        puts("Si5324 does not have expected product number");
        abort();
    }

/*
    // 125MHz
    const int N1_HS  = 1,   // 5
              NC1_LS = 7,   // 8
              N2_HS  = 3,   // 7
              N2_LS  = 359, // 360
              N31    = 62;  // 63
*/
    // 62.5MHz
    const int N1_HS  = 0,   // 4
              NC1_LS = 19,  // 20
              N2_HS  = 1,   // 5
              N2_LS  = 511, // 512
              N31    = 31;  // 32

    si5324_write(2,  (si5324_read(2) & 0x0f) | (bwsel << 4));
    si5324_write(3,  (si5324_read(3)       ) | /*SQ_ICAL=1*/0x10);
    si5324_write(6,  (si5324_read(6) & 0x07) | /*SFOUT1_REG=b111*/0x07);
    si5324_write(25,  N1_HS  << 5);
    si5324_write(31,  NC1_LS >> 16);
    si5324_write(32,  NC1_LS >> 8);
    si5324_write(33,  NC1_LS);
    si5324_write(40, (N2_HS  << 5) | (N2_LS >> 16));
    si5324_write(41,  N2_LS  >> 8);
    si5324_write(42,  N2_LS);
    si5324_write(43,  N31    >> 16);
    si5324_write(44,  N31    >> 8);
    si5324_write(45,  N31);
    si5324_write(137, si5324_read(137) | /*FASTLOCK=1*/0x01);
    si5324_write(136, /*ICAL=1*/0x40);
}

int si5324_has_input()
{
    return (si5324_read(129) & /*LOS1_INT=1*/0x02) == 0;
}

int si5324_has_xtal()
{
    return (si5324_read(129) & /*LOSX_INT=1*/0x01) == 0;
}

int si5324_locked()
{
    return (si5324_read(130) & /*LOL_INT=1*/0x01) == 0;
}

void si5324_set_skew(int8_t skew)
{
    si5324_write(142, skew);
}
