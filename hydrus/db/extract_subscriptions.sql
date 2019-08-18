.print The subscriptions will lose their tag import options, so make sure to check them once they are imported back in.
.open client.db
.out my_subscriptions.sql
.print .open client.db\r\n
.mode insert json_dumps_named
select * from json_dumps_named where dump_type = 3;