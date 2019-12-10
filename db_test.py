import sqlite3

conn = sqlite3.connect('db.sq3')

# create database
cur = conn.executescript(open('schema.sql','r').read())

# populate sensor table
cur.execute('insert into sensors (description) values ("pipe sensor 1")')

# populate state table
cur.execute('insert into states (description) values ("pump off")')
cur.execute('insert into states (description) values ("pump on")')

# populate trigger table
cur.execute('insert into triggers (description) values ("temperature")')
cur.execute('insert into triggers (description) values ("override")')
cur.execute('insert into triggers (description) values ("timeout")')

# commit 
conn.commit()

#>>> pd.read_sql_query("select * from sensors;",conn)
#   id    description
#0   1  pipe sensor 1
#>>> pd.read_sql_query("select * from states;",conn)
#   id description
#0   1    pump off
#1   2     pump on
#>>> pd.read_sql_query("select * from triggers;",conn)
#   id  description
#0   1  temperature
#1   2     override
#2   3      timeout


# Let's try to add some samle measurements
cur.execute('insert into measurements (sensor_id, time, value) values (1, ?, ?);',(datetime.now(),65.0,))
cur.execute('insert into measurements (sensor_id, time, value) values (1, ?, ?);',(datetime.now(),66.0,))
cur.execute('insert into measurements (sensor_id, time, value) values (1, ?, ?);',(datetime.now(),67.0,))

conn.commit()


pd.read_sql_query("SELECT measurements.time, measurements.value, measurements.sensor_id FROM measurements ;",conn)

pd.read_sql_query("""
SELECT measurements.time, measurements.value, sensors.description  
FROM measurements 
INNER JOIN sensors ON measurements.sensor_id = sensors.id;
""",conn)

pd.read_sql_query("""
SELECT statechanges.time, states.description AS new_state, triggers.description AS trigger
FROM statechanges 
INNER JOIN states ON statechanges.new_state = states.id
INNER JOIN triggers ON statechanges.cause = triggers.id
;
""",conn)


pd.read_sql_query("""
SELECT statechanges.time, states.description AS new_state, statechanges.cause
FROM statechanges 
INNER JOIN states ON statechanges.new_state = states.id
;
""",conn)


try:
    cur.execute('insert into measurements (sensor_id, time, value) values (1, ?, ?);',(datetime.now(),77.0,))
    print('that worked')
    conn.commit()
except:
    print("Unable to add to database")


