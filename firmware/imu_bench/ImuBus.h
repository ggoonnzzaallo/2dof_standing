#pragma once
#include <Arduino.h>
#include <nrf_gpio.h>

// Own TWIM1 exclusively: do not initialize Wire1/SPI1 alongside this transport.
// Hardware shortcuts perform repeated-start reads; every wait has a deadline.
class ImuBus {
 public:
  uint32_t lastError = 0, hardwareError = 0; // 1 timeout, 2 peripheral error, 3 short transfer.
  void begin() {
    NVIC_DisableIRQ(SPIM1_SPIS1_TWIM1_TWIS1_SPI1_TWI1_IRQn);
    const uint32_t sda = g_ADigitalPinMap[PIN_WIRE1_SDA];
    const uint32_t scl = g_ADigitalPinMap[PIN_WIRE1_SCL];
    nrf_gpio_cfg(sda, NRF_GPIO_PIN_DIR_INPUT, NRF_GPIO_PIN_INPUT_CONNECT,
                 NRF_GPIO_PIN_PULLUP, NRF_GPIO_PIN_S0D1, NRF_GPIO_PIN_NOSENSE);
    nrf_gpio_cfg(scl, NRF_GPIO_PIN_DIR_INPUT, NRF_GPIO_PIN_INPUT_CONNECT,
                 NRF_GPIO_PIN_PULLUP, NRF_GPIO_PIN_S0D1, NRF_GPIO_PIN_NOSENSE);
    NRF_TWIM1->ENABLE = 0;
    NRF_TWIM1->INTENCLR = 0xffffffff;
    NRF_TWIM1->PSEL.SDA = sda;
    NRF_TWIM1->PSEL.SCL = scl;
    NRF_TWIM1->FREQUENCY = TWIM_FREQUENCY_FREQUENCY_K400;
  }

  bool read(uint8_t address, uint8_t reg, uint8_t *out, size_t count) {
    if (!count || count > 255) return false;
    prepare(address);
    NRF_TWIM1->TXD.PTR = uint32_t(reinterpret_cast<uintptr_t>(&reg));
    NRF_TWIM1->TXD.MAXCNT = 1;
    NRF_TWIM1->RXD.PTR = uint32_t(reinterpret_cast<uintptr_t>(out));
    NRF_TWIM1->RXD.MAXCNT = count;
    NRF_TWIM1->SHORTS = TWIM_SHORTS_LASTTX_STARTRX_Msk | TWIM_SHORTS_LASTRX_STOP_Msk;
    NRF_TWIM1->TASKS_STARTTX = 1;
    const bool ok = complete() && NRF_TWIM1->TXD.AMOUNT == 1 && NRF_TWIM1->RXD.AMOUNT == count;
    if (!ok && !lastError) lastError = 3;
    NRF_TWIM1->ENABLE = 0;
    return ok;
  }

  bool write(uint8_t address, uint8_t reg, uint8_t value) {
    uint8_t bytes[2] = {reg, value};
    prepare(address);
    NRF_TWIM1->TXD.PTR = uint32_t(reinterpret_cast<uintptr_t>(bytes));
    NRF_TWIM1->TXD.MAXCNT = 2;
    NRF_TWIM1->SHORTS = TWIM_SHORTS_LASTTX_STOP_Msk;
    NRF_TWIM1->TASKS_STARTTX = 1;
    const bool ok = complete() && NRF_TWIM1->TXD.AMOUNT == 2;
    if (!ok && !lastError) lastError = 3;
    NRF_TWIM1->ENABLE = 0;
    return ok;
  }

 private:
  void prepare(uint8_t address) {
    lastError = hardwareError = 0;
    NRF_TWIM1->ENABLE = 0;
    NRF_TWIM1->SHORTS = 0;
    NRF_TWIM1->EVENTS_STOPPED = 0;
    NRF_TWIM1->EVENTS_ERROR = 0;
    NRF_TWIM1->EVENTS_LASTTX = 0;
    NRF_TWIM1->EVENTS_LASTRX = 0;
    NRF_TWIM1->ERRORSRC = NRF_TWIM1->ERRORSRC;
    NRF_TWIM1->ADDRESS = address;
    NRF_TWIM1->ENABLE = TWIM_ENABLE_ENABLE_Enabled;
  }

  bool complete() {
    const uint32_t at = micros();
    while (!NRF_TWIM1->EVENTS_STOPPED) {
      if (NRF_TWIM1->EVENTS_ERROR || uint32_t(micros()-at) >= 3000) {
        hardwareError = NRF_TWIM1->ERRORSRC;
        lastError = NRF_TWIM1->EVENTS_ERROR ? 2 : 1;
        NRF_TWIM1->SHORTS = 0;
        NRF_TWIM1->TASKS_RESUME = 1;
        NRF_TWIM1->TASKS_STOP = 1;
        const uint32_t stopAt = micros();
        while (!NRF_TWIM1->EVENTS_STOPPED && uint32_t(micros()-stopAt) < 500) {}
        NRF_TWIM1->ENABLE = 0;
        return false;
      }
    }
    if (NRF_TWIM1->EVENTS_ERROR) {
      hardwareError = NRF_TWIM1->ERRORSRC;
      lastError = 2;
      return false;
    }
    return true;
  }
};
