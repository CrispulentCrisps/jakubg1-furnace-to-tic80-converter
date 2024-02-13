import zlib
import struct

FILE_NAME = "MainTic20.fur"
CHANNEL_COUNT = 4 # depends on sound chip used!
NOTE_PREFIXES = ["  ","C#","D-","D#","E-","F-","F#","G-","G#","A-","A#","B-","C-"]

read_ptr = 0



def open_fur_file(path):
	file = open(FILE_NAME, "rb")
	contents = file.read()
	file.close()

	return zlib.decompress(contents)



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



def format_pattern_line(note, octave, instrument, volume, effects, effect_data):
	s = ""
	if note == 0 and octave == 0:
		s += "--- "
	else:
		if note < 12:
			s += NOTE_PREFIXES[note] + str(octave) + " "
		elif note == 12:
			s += NOTE_PREFIXES[note] + str(octave + 1) + " "
		elif note >= 100:
			s += "^^  "
		else:
			s += "XXX "
	if instrument == 65535:
		s += "-- "
	else:
		if instrument < 10:
			s += "0"
		s += str(instrument) + " "
	if volume == 65535:
		s += "-- "
	else:
		if volume < 10:
			s += "0"
		s += str(volume) + " "
	for i in range(len(effects)):
		effect = effects[i]
		effect_d = effect_data[i]
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
	
	for i in range(len(instrument_ptrs)):
		print("=========== Instrument " + str(i))
		read_ptr = instrument_ptrs[i]
		
		if read_bytes(data, 4) != b"INS2":
			print("INS2 block not found correctly!")
			return
		
		print("INS2 block size: " + str(read_int(data, 4)))
		print("Format version: " + str(read_int(data, 2)))
		print("Instrument type: " + str(read_int(data, 2)))
		print("FEATURES:")
		while True:
			feature_code = read_bytes(data, 2)
			print("Feature code: " + str(feature_code))
			if feature_code == b"EN":
				break
			block_length = read_int(data, 2)
			print("Block length: " + str(block_length))
			if feature_code == b"NA":
				print("Instrument name: " + str(read_string(data)))
			elif feature_code == b"MA":
				print("Macro header length: " + str(read_int(data, 2)))
				while True:
					macro_code = read_int(data, 1)
					print("Code: " + str(macro_code))
					if macro_code == 255:
						break
					macro_length = read_int(data, 1)
					print("Length: " + str(macro_length))
					print("Loop: " + str(read_int(data, 1)))
					print("Release: " + str(read_int(data, 1)))
					print("Mode: " + str(read_int(data, 1)))
					macro_otw = read_int(data, 1)
					macro_wsize = (macro_otw & 192) >> 6
					if macro_wsize == 0 or macro_wsize == 3:
						macro_wsize += 1
					print("Open/Type/Word size: " + str(macro_otw))
					print("Word size: " + str(macro_wsize))
					print("Delay: " + str(read_int(data, 1)))
					print("Speed: " + str(read_int(data, 1)))
					print("Data: " + str(read_bytes(data, macro_length * macro_wsize)))
			else:
				print("Unsupported feature_code: " + str(feature_code) + " Implement me!")
				return
	
	for i in range(len(wavetable_ptrs)):
		print("=========== Wavetable " + str(i))
		read_ptr = wavetable_ptrs[i]
		
		if read_bytes(data, 4) != b"WAVE":
			print("WAVE block not found correctly!")
			return
		
		print("WAVE block size: " + str(read_int(data, 4)))
		print("Wavetable name: " + str(read_string(data)))
		wavetable_width = read_int(data, 4)
		print("Wavetable width: " + str(wavetable_width))
		read_ptr += 4
		print("Wavetable height: " + str(read_int(data, 4)))
		print("Wavetable data: " + str(read_ints(data, 4, wavetable_width)))
	
	for i in range(len(pattern_ptrs)):
		print("=========== Pattern " + str(i))
		read_ptr = pattern_ptrs[i]
		
		if read_bytes(data, 4) != b"PATR":
			print("PATR block not found correctly!")
			return
		
		print("PATR block size: " + str(read_int(data, 4)))
		pattern_channel = read_int(data, 2)
		print("Channel: " + str(pattern_channel))
		print("Pattern index: " + str(read_int(data, 2)))
		print("Subsong: " + str(read_int(data, 2)))
		read_ptr += 2
		for j in range(pattern_length):
			note = read_int(data, 2)
			octave = read_int(data, 2)
			instrument = read_int(data, 2)
			volume = read_int(data, 2)
			effects = []
			effect_data = []
			for k in range(effect_columns[pattern_channel]):
				effects.append(read_int(data, 2))
				effect_data.append(read_int(data, 2))
			print(str(j) + "   " + format_pattern_line(note, octave, instrument, volume, effects, effect_data))
		print("Pattern name: " + str(read_string(data)))



main()