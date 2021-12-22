# Understanding Database Synchronization options

Tuning your database synchronization using the `--db_synchronous_override=0` launch argument can make Hydrus significantly faster with some caveats.

## Key Points

- This is a tutorial for advanced users who have read and understood this document and the risk/recovery procedure.
- It is nearly always safe to use `--db_synchrnous_override=1` on any modern filesystem and this is the default.
- It is always more expensive to access the disk than doing things in memory. SSDs are 10-100x as slow, and HDDs are 1000-10000x as slow as memory.
- If you turn synchronization to `0` you are gambling, but it is a safe gamble if you have a backup and **know exactly** what you are doing
- After running with synchronization set to zero you must either:
  - Exit hydrus normally and let the OS flush disk caches (either by letting the system run/"idle" for a while, running `sync` on *NIX systems, or normal shutdown), or
  - Restore the sqlite database files backup if **the OS shutdown abnormally**.
- Because of the potential for a lot of outstanding writes when using `synchronous=0`, other I/O on your system will slow down as the pending writes are interleaved.  Normal shutdown may also take abnormally long because the system is flushing these pending writes, but you must allow it to take its time as explained in the section below.

In historical versions of hydrus (`synchronous=2`), performance was terrible because hydrus would agressively (it was arguably somewhat paranoid) write changes to disk.

## The Secret Sauce

Setting the synchronous to 0 lets the database engine defer writing to disk as long as physically possible.  In the normal operation of your system, files are constantly being partially transfered to disk, even if the OS pretends they have been fully written to disk.  This is called write cache and it is really important to use it or your system's performance would be terrible.  The caveat is that until you have "`flushed`" the disk cache, the changes to files are not actually in permanent storage.  One purpose of a normal shutdown of the operating system is to make sure all disk caches have been flushed.  A program can also request that a file it has just written to be flushed, and it will wait until that is done before continuing.

When not in synchronous 0 mode, the database engine flushes at regular intervals to make sure data has been written.  
- Setting synchronous to 0 is generally safe **if and only if** the system also shuts down normally, allowing any of these pending writes to be flushed.
- The database can back out of partial changes if hydrus crashes **even if** `synchronous=0`, so your database will not go corrupt from hydrus shutting down abnormally, only from the system shutting down abnormally.

## Technical Explanation

Programmers are responsible for handling partially written files, but this is tedious for large complex data, so they use a database engine which handles all of this.  The database ensures that any partially written data is reversible to a known state (called a rollback).

### An example journal

1. Begin Transaction 1
2. Write Change 1
3. Write Change 2
4. Read data
5. Write Change 3
6. End Transaction 1

Each of these steps are performed in order.  Suppose a crash occcured mid writing

1. Begin Transaction 1
2. Write Change 1
3. Write Cha

When the database resumes it will start scanning the journal at step 1.  Since it will reach the end without seeing `End Transaction 1` it knows that data was only partialy written, and can put the data back in the state before transaction 1 began.  This property of a database is called **atomicity** in the sense that something **atomic** is "indivisible"; either all of the steps in transaction 1 occur or non of them occur.

Hydrus is structured in such a way that the database is written to to keep track of your file catalog only once the file has been fully imported and moved where it is supposed to be.  Thus every action hydrus takes is kept "atomic" or "repeatable" (redo existing work that was partway through).  If hydrus crashes in the middle of importing a file, then when it resumes, as far as it is aware, it didn't even start importing the file.  It will repeat the steps from the start until the file catalog is "consistent" with what is on disk.

### Where synchronization comes in

Lets revisit the journal, this time with two transactions.  Note that the database is flushing after step 6 and thus will have to wait for the OS to write to disk before proceeding, holding up any other access.

1. Begin Transaction 1
2. Write Change 1
3. Write Change 2
4. Read data
5. Write Change 3
6. FLUSH
7. End Transaction 1
8. FLUSH
9. Begin Transaction 2
10. Write Change 2
11. Write Change 2
12. Read data
13. Write Change 3
14. FLUSH
15. End Transaction 2
16. FLUSH

**What happens if we remove step 6 and 8 and then die at step 11?**

1. Begin Transaction 1
2. Write Change 1
3. Write Change 2
4. Read data
5. Write Change 3
~~6. FLUSH~~
7. End Transaction 1
~~8. FLUSH~~
9. Begin Transaction 2
10. Write Change 2
11. Write Ch

What if we crash and step, `End Transaction` has not been written to disk.  Now not only do we need to repeat transaction 2, we also need to repeat transaction 1.  Note that **this just increaeses the ammount of repeatable work, and actually is fully recoverable** (assuming a file you were downloading didn't cease to exist in the interim).

**Now what happens if we do the above and the OS crashes?**
You might be wondering what this has to do with synchronization exactly.  Well the OS is not obligated to write chunks of the database file in the order you give it to them, in fact for harddrives it is optimal to scatter chunks of the file around the spinning disks so it might arbitrarily reorder your write calls.  The only way you can be certain that all of the changes in the transaction have been written before writing `END Transaction` is to `flush()`. The only way to flush is by request of the program or normal closing of the file and final flushing before system power off.  Thus if the OS crashes at the exact wrong moment, there is no way to be sure that the journal is correct if flushing was skipped (`synchronous=0`).  **This means there is no way for you to determine whether the database file is correct after a system crash if you had synchronous 0, and you must restore your files from backup to be sure they are in a known good state.**

So, setting `synchronous=0` gets you a pretty huge speed boost, but you are gambling that everything goes perfectly and will pay the price of a manual restore every time it doesn't.