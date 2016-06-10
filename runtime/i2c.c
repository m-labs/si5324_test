#include <stdio.h>
#include <stdlib.h>
#include <generated/csr.h>
#include "i2c.h"

static void i2c_halfperiod()
{
    timer0_en_write(0);
    timer0_load_write(CONFIG_CLOCK_FREQUENCY/10000);
    timer0_reload_write(0);
    timer0_en_write(1);

    timer0_update_value_write(1);
    while(timer0_value_read() != 0)
        timer0_update_value_write(1);
}

#define SDA_BIT (1 << (2*busno + 1))
#define SCL_BIT (1 << (2*busno))

static int i2c_sda_i(int busno)
{
    return i2c_in_read() & SDA_BIT;
}

static void i2c_sda_oe(int busno, int oe)
{
    int reg;

    reg = i2c_oe_read();
    if(oe)
        reg |= SDA_BIT;
    else
        reg &= ~SDA_BIT;
    i2c_oe_write(reg);
}

static void i2c_sda_o(int busno, int o)
{
    int reg;

    reg = i2c_out_read();
    if(o)
        reg |= SDA_BIT;
    else
        reg &= ~SDA_BIT;
    i2c_out_write(reg);
}

static void i2c_scl_oe(int busno, int oe)
{
    int reg;

    reg = i2c_oe_read();
    if(oe)
        reg |= SCL_BIT;
    else
        reg &= ~SCL_BIT;
    i2c_oe_write(reg);
}

static void i2c_scl_o(int busno, int o)
{
    int reg;

    reg = i2c_out_read();
    if(o)
        reg |= SCL_BIT;
    else
        reg &= ~SCL_BIT;
    i2c_out_write(reg);
}


void i2c_init(int busno)
{
    printf("%s\n", __func__);

    /* Set SCL as output, and high level */
    i2c_scl_o(busno, 1);
    i2c_scl_oe(busno, 1);
    /* Prepare a zero level on SDA so that i2c_sda_oe pulls it down */
    i2c_sda_o(busno, 0);
    /* Release SDA */
    i2c_sda_oe(busno, 0);

    /* Check the I2C bus is ready */
    i2c_halfperiod();
    i2c_halfperiod();
    if(!i2c_sda_i(busno)) {
        puts("SDA is stuck low");
        abort();
    }
}

void i2c_start(int busno)
{
    printf("%s\n", __func__);

    /* Set SCL high then SDA low */
    i2c_scl_o(busno, 1);
    i2c_halfperiod();
    i2c_sda_oe(busno, 1);
    i2c_halfperiod();
}

void i2c_stop(int busno)
{
    printf("%s\n", __func__);

    /* First, make sure SCL is low, so that the target releases the SDA line */
    i2c_scl_o(busno, 0);
    i2c_halfperiod();
    /* Set SCL high then SDA high */
    i2c_sda_oe(busno, 1);
    i2c_scl_o(busno, 1);
    i2c_halfperiod();
    i2c_sda_oe(busno, 0);
    i2c_halfperiod();
}

int i2c_write(int busno, int b)
{
    printf("%s(%02x)\n", __func__, b);

    int i;

    /* MSB first */
    for(i=7;i>=0;i--) {
        /* Set SCL low and set our bit on SDA */
        i2c_scl_o(busno, 0);
        i2c_sda_oe(busno, b & (1 << i) ? 0 : 1);
        i2c_halfperiod();
        /* Set SCL high ; data is shifted on the rising edge of SCL */
        i2c_scl_o(busno, 1);
        i2c_halfperiod();
    }
    /* Check ack */
    /* Set SCL low, then release SDA so that the I2C target can respond */
    i2c_scl_o(busno, 0);
    i2c_halfperiod();
    i2c_sda_oe(busno, 0);
    /* Set SCL high and check for ack */
    i2c_scl_o(busno, 1);
    i2c_halfperiod();
    /* returns 1 if acked (I2C target pulled SDA low) */
    return !i2c_sda_i(busno);
}

int i2c_read(int busno, int ack)
{
    printf("%s(%d)... ", __func__, ack);

    int i;
    unsigned char b;

    /* Set SCL low first, otherwise setting SDA as input may cause a transition
     * on SDA with SCL high which will be interpreted as START/STOP condition.
     */
    i2c_scl_o(busno, 0);
    i2c_halfperiod(); /* make sure SCL has settled low */
    i2c_sda_oe(busno, 0);

    b = 0;
    /* MSB first */
    for(i=7;i>=0;i--) {
        i2c_scl_o(busno, 0);
        i2c_halfperiod();
        /* Set SCL high and shift data */
        i2c_scl_o(busno, 1);
        i2c_halfperiod();
        if(i2c_sda_i(busno)) b |= (1 << i);
    }
    /* Send ack */
    /* Set SCL low and pull SDA low when acking */
    i2c_scl_o(busno, 0);
    if(ack)
        i2c_sda_oe(busno, 1);
    i2c_halfperiod();
    /* then set SCL high */
    i2c_scl_o(busno, 1);
    i2c_halfperiod();

    printf("%02x\n", b);

    return b;
}
