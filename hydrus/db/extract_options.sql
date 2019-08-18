.open client.db
.out my_options.sql
.print .open client.db\r\n
.print delete from options;\r\n
.print delete from json_dumps where dump_type = 22;\r\n
.mode insert options
select * from options;
.mode insert json_dumps
select * from json_dumps where dump_type = 22;