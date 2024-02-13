import zlib
import struct

FILE_NAME = "MainTic20.fur"
CARTRIDGE_NAME = "chainblast.tic"
CHANNEL_COUNT = 4 # depends on sound chip used!
NOTE_PREFIXES = ["  ","C#","D-","D#","E-","F-","F#","G-","G#","A-","A#","B-","C-"]
BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

read_ptr = 0



def open_fur_file(path):
	file = open(path, "rb")
	contents = file.read()
	file.close()

	return zlib.decompress(contents)

def open_tic_file(path):
	file = open(path, "rb")
	contents = file.read()
	file.close()
	
	return contents

def save_tic_file(path, contents):
	file = open(path, "wb")
	file.write(contents)
	file.close()

def unpack_tic_cart(data):
	global read_ptr
	
	read_ptr = 0
	chunks = []
	while read_ptr < len(data):
		chunk = {}
		chunk["type"] = read_int(data, 1)
		chunk["size"] = read_int(data, 2)
		read_ptr += 1
		chunk["data"] = read_bytes(data, chunk["size"])
		chunks.append(chunk)
		print("Chunk of type " + str(chunk["type"]) + " has " + str(chunk["size"]) + " bytes")
	
	return chunks

def pack_tic_cart(chunks):
	data = bytearray()
	for chunk in chunks:
		data.append(chunk["type"])
		data.append(chunk["size"] % 256)
		data.append(int(chunk["size"] / 256))
		data.append(0)
		data += chunk["data"]
	
	return data

def replace_tic_chunk(chunks, type, data):
	for chunk in chunks:
		if chunk["type"] == type:
			chunk["data"] = data
			chunk["size"] = len(data)
			return
	# create a new chunk if not found
	new_chunk = {}
	new_chunk["type"] = type
	new_chunk["data"] = data
	new_chunk["size"] = len(data)
	chunks.append(new_chunk)



def encode_base64(data):
	out = ""
	current_byte = 0
	current_bit = 0
	
	for byte in data:
		for i in range(8):
			n = (byte & (1 << i)) >> i
			current_byte += n << current_bit
			current_bit += 1
			if current_bit == 6:
				out += BASE64_CHARS[current_byte]
				current_byte = 0
				current_bit = 0
	
	if current_bit > 0:
		out += BASE64_CHARS[current_byte]
	# the first byte of the data indicates how many bits are meaningful in the last byte of the data
	out = BASE64_CHARS[(current_bit - 1) % 8 + 1] + out
	
	return out

def decode_base64(data):
	out = bytearray()
	current_byte = 0
	current_bit = 0
	bits_in_last_byte = -1
	
	for i in range(len(data)):
		cn = 0
		for j in range(64):
			if BASE64_CHARS[j] == data[i]:
				cn = j
				break
		if bits_in_last_byte == -1:
			bits_in_last_byte = cn
		else:
			for j in range(6):
				if i == len(data) - 1 and j == bits_in_last_byte:
					break
				n = (cn & (1 << j)) >> j
				current_byte += n << current_bit
				current_bit += 1
				if current_bit == 8:
					out.append(current_byte)
					current_byte = 0
					current_bit = 0
	
	if current_bit > 0:
		out.append(current_byte)
	
	return bytes(out)

def compress_base64(data, orig_data = ""):
	if orig_data == "":
		orig_data = data
	
	best_result = ""
	best_save = 0
	
	for length in range(int(len(data) / 2), 0, -1):
	#for length in range(1, int(len(data) / 2)):
		for offset in range(len(data) - length * 2 + 1):
			base = data[offset:offset+length] # we're essentially iterating over all bases that can be repeated at least one more time right afterwards
			# skip this iteration if the base can be further split
			skip = False
			for i in range(2, int(len(base) / 2) + 1):
				if len(base) % i == 0 and base[:i] * int(len(base) / i) == base:
					skip = True
					break
			if skip:
				continue
			# skip this iteration if the base is already a part of a loop
			if (offset >= length and base == data[offset-length:offset]):
				continue
			n = 1
			while offset+length*(n+1) <= len(data) and base == data[offset+length*n:offset+length*(n+1)]:
				n += 1
			if n > 1:
				result = data[:offset] + "#" + str(n) + "[" + base + "]" + data[offset+length*n:]
				bytes_saved = len(data) - len(result)
				if bytes_saved <= 5: # don't create more trash than it's necessary
					continue
				bytes_saved_total = len(orig_data) - len(result)
				#print("Substring " + base + " repeats " + str(n) + " times")
				#print("Compression result: " + result)
				#print("Bytes saved: " + str(bytes_saved) + " (total: " + str(bytes_saved_total) + ")")
				if bytes_saved_total > best_save:
					best_result = compress_base64(result, orig_data)
					best_save = bytes_saved_total
					#print("New best save! " + str(best_save))
	
	if best_result == "": # the algorithm didn't find a way to shorten the code
		return data
	else:
		return best_result

def decompress_base64(data):
	buffer = [""]
	number_buffer = []
	repeat_step = 0
	
	for char in data:
		if repeat_step == 0:
			if char == "#":
				buffer.append("")
				number_buffer.append(0)
				repeat_step = 1
			elif char == "]":
				buffer[-2] += buffer[-1] * number_buffer.pop()
				buffer.pop()
			else:
				buffer[-1] += char
		elif repeat_step == 1:
			if char == "[":
				repeat_step = 0
			else:
				number_buffer[-1] *= 10
				number_buffer[-1] += int(char)
	
	return buffer[-1]

def count_bytes(data):
	out = {}
	
	for byte in data:
		if byte in out:
			out[byte] += 1
		else:
			out[byte] = 1
	
	return out

def generate_huffman_tree(weights):
	entries = []
	mappings = {}
	for value in weights:
		entries.append({"value": value, "weight": weights[value]})
		mappings[value] = ""
	
	# generate Huffman tree
	while len(entries) > 1:
		entry1 = None # lowest entry
		entry2 = None # second lowest entry
		for entry in entries:
			if entry1 == None or entry["weight"] < entry1["weight"]:
				entry1 = entry
		for entry in entries:
			if (entry2 == None or entry["weight"] < entry2["weight"]) and entry != entry1:
				entry2 = entry
		# entries found, map bits
		update_huffman_mapping(mappings, entry1["value"], "0")
		update_huffman_mapping(mappings, entry2["value"], "1")
		# update the tree
		entries.append({"value": [entry1["value"], entry2["value"]], "weight": entry1["weight"] + entry2["weight"]})
		del entries[entries.index(entry1)]
		del entries[entries.index(entry2)]
	
	return mappings

def update_huffman_mapping(mappings, value, bit):
	if type(value) is list:
		update_huffman_mapping(mappings, value[0], bit)
		update_huffman_mapping(mappings, value[1], bit)
	else:
		mappings[value] = bit + mappings[value]

def invert_huffman_mapping(mapping):
	inverse_mapping = {}
	for byte in mapping:
		inverse_mapping[mapping[byte]] = byte
	return inverse_mapping

def compress_huffman(data, mapping):
	out = bytearray()
	current_byte = 0
	current_bit = 0
	
	for byte in data:
		map = mapping[byte]
		for bit in map:
			current_byte += int(bit) << current_bit
			current_bit += 1
			if current_bit == 8:
				out.append(current_byte)
				current_byte = 0
				current_bit = 0
	
	if current_bit > 0:
		out.append(current_byte)
	# the first byte of the data indicates how many bits are meaningful in the last byte of the data
	out = bytearray([(current_bit - 1) % 8 + 1]) + out
	
	return bytes(out)

def decompress_huffman(data, inverse_mapping):
	out = ""
	current_byte = ""
	bits_in_last_byte = -1
	
	for i in range(len(data)):
		byte = data[i]
		if bits_in_last_byte == -1:
			bits_in_last_byte = byte
		else:
			for j in range(8):
				if i == len(data) - 1 and j == bits_in_last_byte:
					break
				bit = (byte & (1 << j)) >> j
				current_byte += str(bit)
				if current_byte in inverse_mapping:
					out += inverse_mapping[current_byte]
					current_byte = ""
	
	return out



def read_bytes(data, bytes, big_endian = False):
	global read_ptr
	
	out = data[read_ptr:read_ptr+bytes]
	read_ptr += bytes
	if big_endian:
		out = out[::-1]
	return out

def read_int(data, bytes):
	bytes = read_bytes(data, bytes, True)
	num = 0
	for b in bytes:
		num = (num << 8) + b
	return num

def read_ints(data, bytes, count):
	out = []
	for i in range(count):
		out.append(read_int(data, bytes))
	return out

def read_float4(data):
	bytes = read_bytes(data, 4, True)
	return struct.unpack(">f", bytes)[0]

def read_string(data):
	out = b""
	while len(out) == 0 or out[-1] != 0:
		out += read_bytes(data, 1)
	return out[:-1]

def read_strings(data, count):
	out = []
	for i in range(count):
		out.append(read_string(data))
	return out



def format_pattern_row(row):
	s = ""
	
	if row["note"] == 0 and row["octave"] == 0:
		s += "--- "
	else:
		if row["note"] <= 12:
			s += NOTE_PREFIXES[row["note"]] + str(row["octave"]) + " "
		elif row["note"] >= 100:
			s += "^^  "
		else:
			s += "XXX "
	
	if row["instrument"] == 65535:
		s += "-- "
	else:
		if row["instrument"] < 10:
			s += "0"
		s += str(row["instrument"]) + " "
	
	if row["volume"] == 65535:
		s += "-- "
	else:
		if row["volume"] < 10:
			s += "0"
		s += str(row["volume"]) + " "
	
	for i in range(len(row["effects"])):
		effect = row["effects"][i]
		effect_d = row["effect_data"][i]
		if effect == 65535:
			s += "--"
		else:
			if effect < 16:
				s += "0"
			s += hex(effect).upper()[2:]
		if effect_d == 65535:
			s += "--"
		else:
			if effect_d < 16:
				s += "0"
			s += hex(effect_d).upper()[2:]
		s += " "
	
	return s



def get_wavetable(data, ptr):
	global read_ptr
	
	read_ptr = ptr
	
	if read_bytes(data, 4) != b"WAVE":
		print("WAVE block not found correctly!")
		return
	
	out = {}
	
	print("WAVE block size: " + str(read_int(data, 4)))
	out["name"] = read_string(data)
	out["width"] = read_int(data, 4)
	read_ptr += 4
	out["height"] = read_int(data, 4)
	out["data"] = read_ints(data, 4, out["width"])
	
	return out



def get_instrument(data, ptr):
	global read_ptr
	
	read_ptr = ptr
	
	if read_bytes(data, 4) != b"INS2":
		print("INS2 block not found correctly!")
		return
	
	out = {}
	
	print("INS2 block size: " + str(read_int(data, 4)))
	out["version"] = read_int(data, 2)
	out["type"] = read_int(data, 2)
	while True:
		feature_code = read_bytes(data, 2)
		#print("Feature code: " + str(feature_code))
		if feature_code == b"EN":
			break
		block_length = read_int(data, 2)
		#print("Block length: " + str(block_length))
		if feature_code == b"NA":
			out["name"] = read_string(data)
		elif feature_code == b"MA":
			macro_header_length = read_int(data, 2)
			#print("Macro header length: " + str(macro_header_length))
			while True:
				macro = {}
				macro["code"] = read_int(data, 1)
				if macro["code"] == 255:
					break
				macro["length"] = read_int(data, 1)
				macro["loop"] = read_int(data, 1)
				macro["release"] = read_int(data, 1)
				macro["mode"] = read_int(data, 1)
				macro_otw = read_int(data, 1)
				macro["word_size"] = (macro_otw & 192) >> 6
				if macro["word_size"] == 0 or macro["word_size"] == 3:
					macro["word_size"] += 1
				macro["type"] = (macro_otw & 6) >> 1
				macro["delay"] = read_int(data, 1)
				macro["speed"] = read_int(data, 1)
				macro["data"] = read_bytes(data, macro["length"] * macro["word_size"])
				if macro["code"] == 0:
					out["volume"] = macro
				elif macro["code"] == 1:
					out["arpeggio"] = macro
				elif macro["code"] == 2:
					out["duty"] = macro
				elif macro["code"] == 3:
					out["wavetable"] = ord(macro["data"])
				elif macro["code"] == 4:
					out["pitch"] = macro
				else:
					print("Unsupported macro code: " + str(macro["code"]) + " Implement me!")
					return
		else:
			print("Unsupported feature_code: " + str(feature_code) + " Implement me!")
			return
	
	return out



def get_pattern(data, ptr, pattern_length, effect_columns):
	global read_ptr
	
	read_ptr = ptr
	
	if read_bytes(data, 4) != b"PATR":
		print("PATR block not found correctly!")
		return
	
	out = {}
	
	print("PATR block size: " + str(read_int(data, 4)))
	out["channel"] = read_int(data, 2)
	out["index"] = read_int(data, 2)
	out["subsong"] = read_int(data, 2)
	read_ptr += 2
	out["rows"] = []
	for j in range(pattern_length):
		row = {}
		row["note"] = read_int(data, 2)
		row["octave"] = read_int(data, 2)
		if row["note"] == 12:
			row["octave"] += 1
		row["instrument"] = read_int(data, 2)
		row["volume"] = read_int(data, 2)
		row["effects"] = []
		row["effect_data"] = []
		for k in range(effect_columns[out["channel"]]):
			row["effects"].append(read_int(data, 2))
			row["effect_data"].append(read_int(data, 2))
		print(str(j) + "   " + format_pattern_row(row))
		out["rows"].append(row)
	print("Channel: " + str(out["channel"]))
	print("Index: " + str(out["index"]))
	out["name"] = read_string(data)
	
	return out



def convert_wavetable(wavetable):
	out = bytearray()
	low_nibble = True
	
	if len(wavetable["data"]) != 32:
		print("Warning: wavetable " + str(wavetable["name"]) + " not 32 bytes long")
	
	for i in range(32):
		n = int(wavetable["data"][int(i * wavetable["width"] / 32)] * 16 / (wavetable["height"] + 1))
		if low_nibble:
			out.append(n)
		else:
			out[-1] = out[-1] + (n << 4)
		low_nibble = not low_nibble
	
	return bytes(out)



def convert_instrument(instrument):
	print(instrument["name"])
	out = bytearray()
	
	for i in range(30):
		vals = [0, instrument["wavetable"], 0, 0] # volume, wave, arpeggio, pitch
		if "volume" in instrument:
			decay = instrument["volume"]["data"][4]
			vals[0] = int(15 - (15 / (decay ** (i/25))))
		if "duty" in instrument:
			if i >= instrument["duty"]["length"]:
				if instrument["duty"]["data"][-1] > 0:
					vals[1] = 15
			elif instrument["duty"]["data"][i] > 0:
				vals[1] = 15
		if "arpeggio" in instrument and i < instrument["arpeggio"]["length"]:
			vals[2] = instrument["arpeggio"]["data"][i]
		if "pitch" in instrument and i < instrument["pitch"]["length"] and instrument["pitch"]["type"] == 0: # HACK
			n = instrument["pitch"]["data"][i * 2 + 1]
			if n > 128:
				n -= 240
			vals[3] = min(max(n, 0), 15)
		
		### MEGA HACK: I'm tweaking these values for myself, if you want to generalize the code REMOVE THIS BLOCK !!!
		if instrument["name"] == b"Kick":
			vals[2] = min(i * 3, 15)
			vals[3] = max(10 - i, 8)
		elif instrument["name"] == b"Snare" and vals[3] == 14:
			vals[3] = 10
		### END OF MEGA HACK (but look at the lines below!)
		
		out.append(vals[0] + (vals[1] << 4))
		out.append(vals[2] + (vals[3] << 4))
	
	if instrument["name"] == b"Kick": ### PART OF MEGA HACK
		out.append(140) # 128+8+4 (128=arp down,8=16x pitch,4=speed)
	else:
		out.append(12) # 8+4 (8=16x pitch,4=speed)
	out.append(0)
	out.append(0) # vol loop
	out.append(0) # wave loop
	if "arpeggio" in instrument and instrument["arpeggio"]["loop"] != 255:
		out.append(((instrument["arpeggio"]["length"] - instrument["arpeggio"]["loop"]) << 4) + instrument["arpeggio"]["loop"])
	else:
		out.append(0)
	if "pitch" in instrument and instrument["pitch"]["loop"] != 255 and instrument["name"] != b"Kick": ### the name comparison is also part of the MEGA HACK
		out.append(((instrument["pitch"]["length"] - instrument["pitch"]["loop"]) << 4) + instrument["pitch"]["loop"])
	else:
		out.append(0)
	
	return bytes(out)



def convert_pattern(pattern, prev_pattern = None):
	out = bytearray()
	
	last_instrument = 0
	slide_active = False
	# we need more patterns in order to look at the last instrument
	if prev_pattern != None:
		for row in prev_pattern["rows"]:
			if row["instrument"] != 65535:
				last_instrument = row["instrument"]
	
	for row in pattern["rows"]:
		vals = [0, 0, 0, 0, 0, 0] # note, p1, p2, command, instrument, octave
		
		if row["note"] >= 100:
			vals[0] = 1
		elif row["note"] == 12:
			vals[0] = 4
		elif row["note"] != 0 and row["note"] < 12:
			vals[0] = row["note"] + 4
		
		if row["instrument"] != 65535:
			vals[4] = row["instrument"]
			last_instrument = row["instrument"]
		elif row["note"] > 0 and row["note"] <= 12:
			vals[4] = last_instrument
		
		vals[5] = row["octave"] + 1
		
		if row["effects"][0] == 0 and row["effect_data"][0] != 65535:
			vals[3] = 2
			vals[1] = int(row["effect_data"][0] / 16)
			vals[2] = row["effect_data"][0] % 16
		elif row["effects"][0] == 3:
			vals[3] = 4
			n = max(1, row["effect_data"][0]) * 4
			if row["effect_data"][0] == 65535:
				n = 4
			vals[1] = int(n / 16)
			vals[2] = n % 16
			slide_active = True
		elif row["note"] != 0 and slide_active: # slide needs to be cancelled manually
			vals[3] = 4
			# params remain zero
			slide_active = False
		
		out.append(vals[0] + (vals[1] << 4))
		out.append(vals[2] + (vals[3] << 4) + ((vals[4] & 32) << 2))
		out.append((vals[4] & 31) + (vals[5] << 5))
	
	return bytes(out)



def main():
	global read_ptr
	
	data = open_fur_file(FILE_NAME)
	
	if read_bytes(data, 16) != b"-Furnace module-":
		print("It's not a valid file or the decompression went wrong!")
		return
	
	print("Version number: " + str(read_int(data, 2)))
	read_ptr += 2
	song_info_ptr = read_int(data, 4)
	read_ptr = song_info_ptr
	
	if read_bytes(data, 4) != b"INFO":
		print("INFO block not found correctly!")
		return
	
	print("=========== INFO block size: " + str(read_int(data, 4)))
	print("Time base: " + str(read_int(data, 1)))
	print("Speed 1: " + str(read_int(data, 1)))
	print("Speed 2: " + str(read_int(data, 1)))
	print("Initial arp time: " + str(read_int(data, 1)))
	print("Ticks per second: " + str(read_float4(data)))
	pattern_length = read_int(data, 2)
	print("Pattern length: " + str(pattern_length))
	orders_length = read_int(data, 2)
	print("Orders length: " + str(orders_length))
	print("Highlight A: " + str(read_int(data, 1)))
	print("Highlight B: " + str(read_int(data, 1)))
	
	instrument_count = read_int(data, 2)
	print("Instrument count: " + str(instrument_count))
	wavetable_count = read_int(data, 2)
	print("Wavetable count: " + str(wavetable_count))
	sample_count = read_int(data, 2)
	print("Sample count: " + str(sample_count))
	pattern_count = read_int(data, 4)
	print("Pattern count: " + str(pattern_count))
	
	print("Sound chips:")
	soundchip_bytes = read_bytes(data, 32)
	for b in soundchip_bytes:
		if b == 0:
			break
		else:
			print(b)
	soundchip_volumes = read_bytes(data, 32)
	soundchip_panning = read_bytes(data, 32)
	soundchip_flagptrs = read_bytes(data, 128)
	
	print("Song name: " + str(read_string(data)))
	print("Song author: " + str(read_string(data)))
	print("A-4 tuning: " + str(read_float4(data)))
	print("Limit slides: " + str(read_int(data, 1)))
	print("Linear pitch: " + str(read_int(data, 1)))
	print("Loop modality: " + str(read_int(data, 1)))
	print("Proper noise layout: " + str(read_int(data, 1)))
	print("Wave duty is volume: " + str(read_int(data, 1)))
	print("Reset macro on porta: " + str(read_int(data, 1)))
	print("Legacy volume slides: " + str(read_int(data, 1)))
	print("Compatible arpeggio: " + str(read_int(data, 1)))
	print("Note off resets slides: " + str(read_int(data, 1)))
	print("Target resets slides: " + str(read_int(data, 1)))
	print("Arpeggio inhibits portamento: " + str(read_int(data, 1)))
	print("Wack algorithm macro: " + str(read_int(data, 1)))
	print("Broken shortcut slides: " + str(read_int(data, 1)))
	print("Ignore duplicate slides: " + str(read_int(data, 1)))
	print("Stop portamento on note off: " + str(read_int(data, 1)))
	print("Continuous vibrato: " + str(read_int(data, 1)))
	print("Broken DAC mode: " + str(read_int(data, 1)))
	print("One tick cut: " + str(read_int(data, 1)))
	print("Instrument change allowed during porta: " + str(read_int(data, 1)))
	print("Reset note base on arpeggio effect stop: " + str(read_int(data, 1)))
	
	instrument_ptrs = read_ints(data, 4, instrument_count)
	print("Instrument pointers: " + str(instrument_ptrs))
	wavetable_ptrs = read_ints(data, 4, wavetable_count)
	print("Wavetable pointers: " + str(wavetable_ptrs))
	sample_ptrs = read_ints(data, 4, sample_count)
	print("Sample pointers: " + str(sample_ptrs))
	pattern_ptrs = read_ints(data, 4, pattern_count)
	print("Pattern pointers: " + str(pattern_ptrs))
	
	orders = read_bytes(data, CHANNEL_COUNT * orders_length)
	print("Orders: " + str(orders))
	effect_columns = read_bytes(data, CHANNEL_COUNT)
	print("Effect columns: " + str(effect_columns))
	channel_hide_status = read_bytes(data, CHANNEL_COUNT)
	channel_collapse_status = read_bytes(data, CHANNEL_COUNT)
	print("Channel names: " + str(read_strings(data, CHANNEL_COUNT)))
	print("Channel short names: " + str(read_strings(data, CHANNEL_COUNT)))
	print("Song comment: " + str(read_string(data)))
	print("Master volume: " + str(read_float4(data)))
	print("Extended compatibility flags: " + str(read_bytes(data, 28)))
	print("Virtual tempo numerator: " + str(read_int(data, 2)))
	print("Virtual tempo denominator: " + str(read_int(data, 2)))
	print("First subsong name: " + str(read_string(data)))
	print("First subsong comment: " + str(read_string(data)))
	subsong_count = read_int(data, 1)
	print("Subsong count: " + str(subsong_count))
	read_ptr += 3
	subsong_ptrs = read_ints(data, 4, subsong_count)
	print("Subsong pointers: " + str(subsong_ptrs))
	print("System name: " + str(read_string(data)))
	print("Album/category/game name: " + str(read_string(data)))
	print("Song name (JP): " + str(read_string(data)))
	print("Song author (JP): " + str(read_string(data)))
	print("System name (JP): " + str(read_string(data)))
	print("Album/category/game name (JP): " + str(read_string(data)))
	print("Chip volume: " + str(read_float4(data)))
	print("Chip panning: " + str(read_float4(data)))
	print("Chip balance: " + str(read_float4(data)))
	patchbay_connection_count = read_int(data, 4)
	patchbay_connections = read_ints(data, 4, patchbay_connection_count)
	print("Patchbay connections: " + str(patchbay_connections))
	print("Automatic patchbay: " + str(read_int(data, 1)))
	print("Broken portamento during legato: " + str(read_int(data, 1)))
	read_ptr += 7
	print("Speed pattern speed: " + str(read_int(data, 1)))
	print("Speed pattern: " + str(read_bytes(data, 16)))
	print("Groove entries: " + str(read_int(data, 1)))
	
	instruments = []
	for i in range(len(instrument_ptrs)):
		print("=========== Instrument " + str(i))
		instrument = get_instrument(data, instrument_ptrs[i])
		instruments.append(instrument)
		print(str(instrument))
	
	wavetables = []
	for i in range(len(wavetable_ptrs)):
		print("=========== Wavetable " + str(i))
		wavetable = get_wavetable(data, wavetable_ptrs[i])
		wavetables.append(wavetable)
		#print(str(wavetable))
	
	patterns = []
	for i in range(len(pattern_ptrs)):
		print("=========== Pattern " + str(i))
		pattern = get_pattern(data, pattern_ptrs[i], pattern_length, effect_columns)
		patterns.append(pattern)
		#print(str(pattern))
	
	pattern_order = []
	tracks = []
	order = 0
	start_from_second_half = False
	for i in range(8):
		track = bytearray()
		while len(track) < 48: # max 16 patterns but we divide by 2 because TIC supports 64-long and we have 128-long patterns here
			if order < orders_length:
				vals = [0, 0, 0, 0] # patterns for four channels
				skip_second_half = False
				for channel in range(4):
					pattern_in_channel = 0
					pattern_in_total = 0
					for pattern in patterns:
						if pattern["channel"] != channel:
							pattern_in_total += 1
							continue
						if pattern_in_channel == orders[channel * orders_length + order]:
							vals[channel] = pattern_in_total
							if pattern["rows"][63]["effects"][0] == 13: # is there a "jump to next pattern" command in the middle of a pattern?
								print("Jump found in pattern!")
								skip_second_half = True
							break
						pattern_in_channel += 1
						pattern_in_total += 1
				# insert both halves (unless we're skipping the second one)
				for k in range(2):
					if start_from_second_half: # skip first half if we're starting from the second one
						start_from_second_half = False
						continue
					if k == 1 and skip_second_half:
						break
					v0 = vals[0] * 2 + k + 1
					v1 = vals[1] * 2 + k + 1
					v2 = vals[2] * 2 + k + 1
					v3 = vals[3] * 2 + k + 1
					pattern_order.append([v0, v1, v2, v3])
					track.append(v0 + ((v1 & 3) << 6))
					track.append((v1 >> 2) + ((v2 & 15) << 4))
					track.append((v2 >> 4) + (v3 << 2))
					if len(track) == 48: # if we've filled the track in the middle of a pattern, stop here and continue on with the next track
						start_from_second_half = True
						break
				if not start_from_second_half:
					order += 1
			else:
				track += bytearray([0, 0, 0])
		# tempo, speed and amount of rows
		track.append(256 - 30)
		track.append(0)
		track.append(0)
		
		tracks.append(track)
		print("Track " + str(i) + ": " + str(track) + " (len " + str(len(track)) + ")")
		print("Encoded: " + encode_base64(track) + " (len " + str(len(encode_base64(track))) + ")")
	
	
	
	# Conversion
	converted_wavetables = b""
	print("Converted wavetables:")
	for wavetable in wavetables:
		converted = convert_wavetable(wavetable)
		converted_wavetables += converted
		print(str(wavetable))
		#print(str(converted))
	
	converted_instruments = b""
	print("Converted instruments:")
	for instrument in instruments:
		converted = convert_instrument(instrument)
		converted_instruments += converted
		#print(str(converted))
	
	converted_patterns = b""
	print("Converted patterns:")
	prev_pattern = None
	b64_testtotal = 0
	b64_testtotal2 = 0
	b64_testdifftotal = 0
	b64_patterns = []
	for pattern in patterns:
		converted = convert_pattern(pattern, prev_pattern)
		converted_patterns += converted
		#print(str(converted))
		
		for i in range(2):
			print("==================== B64 START")
			b64_test = encode_base64(converted[i*192:(i+1)*192]).replace("AAAI", "@").replace("IAA", "$").replace("IAQh", "%").replace("Ago", "^")
			b64_testtotal += len(b64_test)
			print(b64_test + " (" + str(len(b64_test)) + ")")
			b64_test2 = compress_base64(b64_test)
			b64_testtotal2 += len(b64_test2)
			b64_testdiff = len(b64_test2) - len(b64_test)
			b64_testdifftotal -= b64_testdiff
			print(b64_test2 + " (" + str(len(b64_test2)) + ") [" + str(b64_testdiff) + "]")
			b64_patterns.append(b64_test2)
			print("==================== B64 END")
		
		prev_pattern = pattern
	
	print("Total income: " + str(b64_testdifftotal) + " (" + str(b64_testtotal) + " -> " + str(b64_testtotal2) + ")")
	
	
	comp_huff_bytes = count_bytes(converted_patterns)
	#print(comp_huff_bytes)
	comp_huff_tree = generate_huffman_tree(comp_huff_bytes)
	#print(comp_huff_tree)
	print("Bytes before: " + str(len(converted_patterns)))
	comp_test_bits = 0
	for byte in comp_huff_bytes:
		comp_test_bits += len(comp_huff_tree[byte]) * comp_huff_bytes[byte]
	print("Bytes after (expected): " + str(comp_test_bits / 8))
	
	comp_huff_tree2 = generate_huffman_tree(count_bytes("".join(b64_patterns)))
	comp_huff_map_inv = invert_huffman_mapping(comp_huff_tree2)
	comp_test_bytes = 0
	for i in range(len(b64_patterns)):
		pattern = encode_base64(compress_huffman(b64_patterns[i], comp_huff_tree2))
		comp_test_bytes += len(pattern)
		print(pattern)
		step1 = decode_base64(pattern)
		print("Decoding step 1: " + str(step1))
		step2 = decompress_huffman(step1, comp_huff_map_inv)
		print("Decoding step 2: " + str(step2))
		step3 = decompress_base64(step2.replace("@", "AAAI").replace("$", "IAA").replace("%", "IAQh").replace("^", "Ago"))
		print("Decoding step 3: " + str(step3))
		step4 = decode_base64(step3)
		print("Decoding step 4: " + str(step4))
		if step4 in converted_patterns:
			print("YES!")
		else:
			print("NO!")
		print(str(i) + " " + str(len(step1)) + " " + str(len(step2)) + " " + str(len(step3)) + " " + str(len(step4)))
		b64_patterns[i] = pattern
	print("Bytes after (real): " + str(comp_test_bytes))
	
	
	converted_tracks = b""
	for track in tracks:
		converted_tracks += track
	
	
	
	# TIC and export
	cart_data = open_tic_file(CARTRIDGE_NAME)
	cart_chunks = unpack_tic_cart(cart_data)
	replace_tic_chunk(cart_chunks, 10, converted_wavetables)
	replace_tic_chunk(cart_chunks, 9, converted_instruments)
	replace_tic_chunk(cart_chunks, 15, converted_patterns)
	replace_tic_chunk(cart_chunks, 14, converted_tracks)
	new_cart_data = pack_tic_cart(cart_chunks)
	save_tic_file(CARTRIDGE_NAME, new_cart_data)
	
	music_data = "M_DATA = {\n"
	for pattern in b64_patterns:
		music_data += "\t\"" + pattern + "\",\n"
	music_data += "}\n"
	
	comp_huff_map_inv_l = [None, None]
	current_table = comp_huff_map_inv_l
	for key in comp_huff_map_inv:
		byte = comp_huff_map_inv[key]
		for i in range(len(key)):
			bit = int(key[i])
			if i < len(key) - 1:
				if current_table[bit] == None:
					current_table[bit] = [None, None]
				current_table = current_table[bit]
			else:
				current_table[bit] = byte
				current_table = comp_huff_map_inv_l
	music_data += "M_CODE = " + str(comp_huff_map_inv_l).replace("[", "{").replace("]", "}").replace(", ", ",").replace("'", "\"") + "\n"
	music_data += "M_PATTERNS = " + str(pattern_order).replace("[", "{").replace("]", "}").replace(", ", ",") + "\n"
	
	file = open("music_data.txt", "w")
	file.write(music_data)
	file.close()
	
	
	
	#print(compress_base64("AAAAAABBBBBBAAAAAABBBBBBAAAAAABBBBBB"))
	#for i in range(40):
	#	print(compress_base64("ABABABABABABAB" * i))
	#print(decompress_base64("ABC#5[DEF#3[GHI]]XYZ"))



main()