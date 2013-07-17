#!/usr/bin/python

# Convert

#    Convert - Python module to convert number and data type
#
#    Copyright (C) 2002 Thomas Mangin
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys

__oct='01234567'
__dec='0123456789'
__hex='0123456789abcdefABCDEF'

__size = { 10:0, 8:1, 16:2 }

# Assume that the string have the appropriate length for tests

def __is_cross(char):
	return char in "xX"

def __is_digit_start(char):
	return char in "0\\"

def __is_oct_digit(char):
	return char in __oct

def __is_dec_digit(char):
	return char in __dec

def __is_hex_digit(char):
	return char in __hex


def __is_oct_start(text):
	return __is_digit_start(text[0]) and __is_oct_digit(text[1])

def __is_dec_start(text):
	return __is_dec_digit(text[0])

def __is_hex_start(text):
	return __is_digit_start(text[0]) and __is_cross(text[1]) and  __is_hex_digit(text[2])


def __is_number_start(text):
	# The order of the test are important as they can raise exceptions
	return \
		__is_dec_start(text) or \
		__is_oct_start(text) or \
		__is_hex_start(text)

# End of Assume

def base10 (text,base):
	number = str(text).lower()
	result=0L
	for digit in number:
		result*=base
		pos = __hex.index(digit)
		result+=pos
	return result


def which_base(text):
	# return the base in (8,10,16) or 0 if not a number
	length = len(text)
	text.lower()

	if length > 2 and __is_hex_start(text):
		return 16

	if length > 1 and __is_oct_start(text):
		return 8

	if length > 0 and __is_dec_start(text):
		return 10

	return 0


def start_base(text):
	return which_base(text) != 0

def size_base(base):
	return __size[base]

def size_number(text):
	base = which_base(text)

	if base == 0:
		return 0

	length = len(text)
	size = size_base(base)
	end = size+1

	while end < length and text[end] in __hex[:base]:
		end += 1 
	return end


def index_number(text):
	index=0
	try:
		while 1:
			if __is_number_start(text[index:]):
				break
			index += 1
	except:
		# for the offstring access
		index = -1

	return index

def convert (text):
	base = which_base(text)
	start = size_base(base)
	end = size_number(text)	
	return base10(text[start:end],base)


# Special function to extract numbers from strings
# Should not be really be here !

def is_final_dash (text):
	if len(text) < 2:
		return text[-1] == '\\' 
	else:
		return text[-1] == '\\' and text[-2] != '\\'

def is_c_escape (text):
	if len (text) < 2:
		return 0
	elif text[0] != '\\':
		return 0
	# I am probably missing some but do not have C book nearby
	if text[1] in "nrb0":
		return 1
	return 0

# End special function

def little2 (number):
	low = ord(number[0])
	high = ord(number[1])

	return (high << 8) + low
	
def little4 (number):
	low = long(little2(number))
	high = long(little2(number[2:]))

	return (high << 16) + low

def big2 (number):
	low = ord(number[1])
	high = ord(number[0])

	return (high << 8) + low

def big4 (number):
	low = long(big2(number[2:]))
	high = long(big2(number))

	return (high << 16) + low

def local2 (number):
	if sys.byteorder == 'big':
		return big2(number)
	return little2(number)

def local4 (number):
	if sys.byteorder == 'big':
		return big4(number)
	return little4(number)


if __name__ == '__main__':
	print "---"
	print "base10(\"FF\",16) = ", 255, "\tgot ", base10("FF",16)
	print "base10(\"77\", 8) = ",  63, "\tgot ", base10("77",8)

	print "---"
	print "convert(\"0xFF\"  ) = ",  255, "\tgot ", convert("0xFF")
	print "convert(\"\\xFF\"  ) = ", 255, "\tgot ", convert("\\xFF")
	print "convert(\"077\"   ) = ",   63, "\tgot ", convert("077")
	print "convert(\"\\77\"   ) = ",  63, "\tgot ", convert("\\77")
	print "convert(\"\\177E\"   ) = ",  127, "\tgot ", convert("\\177E"), "The E is not used"

	print "---"
	print "size_number(\"100FFF\") = ",   3, "\tgot", size_number("100qwerty")
	print "size_number(\"\\7799\" ) = ",  3, "\tgot", size_number("\\77FF")
	print "size_number(\"\\XFFG\" ) = ",  3, "\tgot", size_number("\\XFFG")

	print "---"
	print "index_number(\"0XF\"       ) = ",   0, "\tgot", index_number("0XF")
	print "index_number(\"\\XF\"       ) = ",   0, "\tgot", index_number("\\XF")
	print "index_number(\"FF\\FFGG\"   ) = ",  -1, "\tgot", index_number("FF\\FFGG")
	print "index_number(\"FF\\7\"      ) = ",   2, "\tgot", index_number("FF\\7")
	print "index_number(\"FFF\\XFFGG\" ) = ",   3, "\tgot", index_number("FFF\\XFFGG")
	print "index_number(\"\\\\\\XFFGG\"  ) = ",   2, "\tgot", index_number("FF\\XFFGG")


	# 0000 0001 -->     1
	# 0001 0000 -->    16
	# 0001 1000 -->    24
	# 1000 0001 -->   129
	# 0000 0001 1000 0000 -->   384
	# 1000 0000 0000 0001 --> 32769
	# 0000 0000 0000 0001 1000 0000 0000 0000 --> 98304
	# 0000 0000 1000 0000 0000 0001 0000 0000 --> 8388864
	# 1000 0000 0000 0000 0000 0000 0000 0001 --> 2147483649


	print "---"
	print "little2   ","1    ",little2(chr( 1)+chr(0))
	print "little2   ","16   ",little2(chr(16)+chr(0))

	print "---"
	print "big2","1    ",big2(chr(0)+chr(1))
	print "big2","16   ",big2(chr(0)+chr(16))

	print "---"
	print "little4","2147483649",little4(chr(1)+chr(0)+chr(0)+chr(128))
	print "big4   ","2147483649",big4(chr(128)+chr(0)+chr(0)+chr(1))


