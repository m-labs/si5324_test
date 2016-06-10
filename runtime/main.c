#include <stdio.h>
#include <irq.h>
#include <uart.h>

int main(void)
{
    irq_setmask(0);
    irq_setie(1);
    uart_init();

    puts("Si5324 runtime built "__DATE__" "__TIME__"\n");

    while(1);
}
