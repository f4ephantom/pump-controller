import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

db = sqlite3.connect('database.sq3')

query = """
SELECT measurements.time, measurements.value
FROM measurements
WHERE measurements.time > datetime('now','-1 days');
"""

df = pd.read_sql_query(query,db)
df['time'] = pd.to_datetime(df['time'])

plt.plot(df['time'],df['value'])
myFMT = mdates.DateFormatter('%H:%M')
plt.gca().xaxis.set_major_formatter(myFMT)
plt.ylabel(r'Temperature [$^o$F]')
plt.savefig('temp24.png',dpi=150)
plt.show()

