# FTMO Timestamp Validation

## Validation environment

- Validation date: 2026-11-26
- Broker: FTMO Global Markets Ltd
- Server: FTMO-Server3
- Instrument: US100.cash
- Timeframe: M1
- MT5 Python version: 5.0.5735
- Maximum historical bars: 100000000

## Historical summer validation

Date: 2025-07-04

- Candles returned: 1135
- Final original MT5 timestamp: 1751659140
- Direct UTC interpretation: 19:59
- Corrected UTC timestamp: 16:59
- Official UTC market closure: 17:00
- Expected final M1 candle: 16:59
- Difference: 0 seconds
- Result: PASS

Source:
https://ftmo.com/en/blog/trading-updates/trading-update-3-jul-2025/

## Historical winter validation

Date: 2025-11-27

- Candles returned: 1135
- Final original MT5 timestamp: 1764273540
- Direct UTC interpretation: 19:59
- Corrected UTC timestamp: 17:59
- Official UTC market closure: 18:00
- Expected final M1 candle: 17:59
- Difference: 0 seconds
- Result: PASS

Source:
https://ftmo.com/en/blog/trading-updates/trading-update-27-nov-2025/

## Daylight saving convention

FTMO platform time follows US daylight saving transitions.

- Winter: UTC+2
- Summer: UTC+3

Source:
https://ftmo.com/au/blog/trading-updates/trading-update-6-mar-2025/

## Conclusion

The sampled FTMO-Server3 observations support the existing
broker-clock conversion implemented in src/ftmo_time.py.

Original MT5 integer timestamps are preserved as mt5_time_raw.
Converted timestamps are stored in datetime.

## Limitations

- These checks do not establish complete historical coverage.
- Not every historical year has been independently validated.
- Other MT5 brokers and servers remain unverified.
- The maximum historical bar setting does not guarantee availability.
- Automated conversion tests are separate from live broker validation.

## Future improvements

Introduce broker-independent and server-independent timestamp
configuration without sacrificing data integrity.
