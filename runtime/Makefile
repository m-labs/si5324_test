include ../include/generated/variables.mak
include $(MISOC_DIRECTORY)/software/common.mak

OBJECTS := main.o isr.o i2c.o pca9548.o si5324.o

all: runtime.bin

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@
	@chmod -x $@

runtime.elf: $(OBJECTS)
	$(LD) $(LDFLAGS) \
		-T $(RUNTIME_DIRECTORY)/runtime.ld \
		-N -o $@ \
		../libbase/crt0-$(CPU).o \
		$(OBJECTS) \
		-L../libcompiler_rt \
		-L../libbase \
		-lbase-nofloat -lcompiler_rt
	@chmod -x $@

%.o: $(RUNTIME_DIRECTORY)/%.c
	$(compile)

%.o: $(RUNTIME_DIRECTORY)/%.S
	$(assemble)

clean:
	$(RM) $(OBJECTS) $(OBJECTS_KSUPPORT)
	$(RM) runtime.elf runtime.bin .*~ *~

.PHONY: all clean
