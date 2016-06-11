#ifndef __SI5324_H
#define __SI5324_H

#include <stdint.h>

void si5324_reset(void);
void si5324_write(uint8_t reg, uint8_t val);
uint8_t si5324_read(uint8_t reg);

uint16_t si5324_ident(void);
void si5324_init_125MHz(int bwsel);
int si5324_locked(void);
int si5324_active(void);

#endif
