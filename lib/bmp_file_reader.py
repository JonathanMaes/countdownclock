# Minified from https://raw.githubusercontent.com/ExcaliburZero/bmp_file_reader/master/bmp_file_reader.py
# MIT License, Copyright (c) 2021 Christopher Wells
# Prepare a .bmp with command: magick convert <input> -type truecolor <out.bmp>
_C=False
_B='little'
_A=None
import math
class BMPFileReader:
	def __init__(A,file_handle):A.file_handle=file_handle;A.__bmp_header=_A;A.__dib_header=_A
	def read_bmp_file_header(A):
		if A.__bmp_header is not _A:return A.__bmp_header
		A.file_handle.seek(0);C=A.file_handle.read(14);B=BMPHeader.from_bytes(C);A.__bmp_header=B;return B
	def read_dib_header(A):
		if A.__dib_header is not _A:return A.__dib_header
		A.file_handle.seek(14);B=DIBHeader.from_positioned_file_handler(A.file_handle);A.__dib_header=B;return B
	def get_width(A):return A.read_dib_header().width
	def get_height(A):return A.read_dib_header().height
	def get_row(A,row):
		F=3;C=A.read_dib_header().bits_per_pixel
		if C!=24:raise ValueError('This parser does not currently support BMP files with {} bits per pixel. Currently only 24-bit color values are supported.'.format(C))
		G=A.read_dib_header().compression_type
		if G!=CompressionType.BI_RGB:raise ValueError('This parser does not currently support compressed BMP files.')
		H=A.get_height();I=H-row-1;D=int(math.ceil(F*A.get_width()/4.)*4);J=A.read_bmp_file_header().image_start_offset+D*I;A.file_handle.seek(J);K=list(bytearray(A.file_handle.read(D)));E=[];B=0
		while B<A.get_width():L=B*3;M=(B+1)*3;E.append(Color.from_bytes(K[L:M]));B+=1
		return E
class Color:
	red=0;green=0;blue=0
	def __init__(A,red,green,blue):A.red=red;A.green=green;A.blue=blue
	def __repr__(A):return'Color(red={}, green={}, blue={})'.format(A.red,A.green,A.blue)
	def __eq__(B,other):
		A=other
		if not isinstance(A,Color):return _C
		return B.red==A.red and B.green==A.green and B.blue==A.blue
	@staticmethod
	def from_bytes(color_bytes):A=color_bytes;B=A[0];C=A[1];D=A[2];return Color(D,C,B)
class BMPHeader:
	def __init__(A,bmp_type,size,value_1,value_2,image_start_offset):A.bmp_type=bmp_type;A.size=size;A.value_1=value_1;A.value_2=value_2;A.image_start_offset=image_start_offset
	def __repr__(A):return'BMPHeader(bmp_type={}, size={}, value_1={}, value_2={}, image_start_offset={})'.format(A.bmp_type,A.size,A.value_1,A.value_2,A.image_start_offset)
	def __eq__(B,other):
		A=other
		if not isinstance(A,BMPHeader):return _C
		return B.bmp_type==A.bmp_type and B.size==A.size and B.value_1==A.value_1 and B.value_2==A.value_2 and B.image_start_offset==A.image_start_offset
	@staticmethod
	def from_bytes(header_bytes):A=list(bytearray(header_bytes));B=BMPType.from_bytes(A[0:2]);C=int.from_bytes(bytes(A[2:6]),_B);D=bytes(A[6:8]);E=bytes(A[8:10]);F=int.from_bytes(bytes(A[10:14]),_B);return BMPHeader(B,C,D,E,F)
class DIBHeader:
	def __init__(A,width,height,num_color_planes,bits_per_pixel,compression_type,raw_bitmap_size,horizontal_resolution_ppm,vertical_resolution_ppm,num_colors_in_palette,num_important_colors_used):A.width=width;A.height=height;A.num_color_planes=num_color_planes;A.bits_per_pixel=bits_per_pixel;A.compression_type=compression_type;A.raw_bitmap_size=raw_bitmap_size;A.horizontal_resolution_ppm=horizontal_resolution_ppm;A.vertical_resolution_ppm=vertical_resolution_ppm;A.num_colors_in_palette=num_colors_in_palette;A.num_important_colors_used=num_important_colors_used
	def __eq__(B,other):
		A=other
		if not isinstance(A,DIBHeader):return _C
		return B.width==A.width and B.height==A.height and B.num_color_planes==A.num_color_planes and B.bits_per_pixel==A.bits_per_pixel and B.compression_type==A.compression_type and B.raw_bitmap_size==A.raw_bitmap_size and B.horizontal_resolution_ppm==A.horizontal_resolution_ppm and B.vertical_resolution_ppm==A.vertical_resolution_ppm and B.num_colors_in_palette==A.num_colors_in_palette and B.num_important_colors_used==A.num_important_colors_used
	def __repr__(A):return'DIBHeader(\n    width={},\n    height={},\n    num_color_planes={},\n    bits_per_pixel={},\n    compression_type={},\n    raw_bitmap_size={},\n    horizontal_resolution_ppm={},\n    vertical_resolution_ppm={},\n    num_colors_in_palette={},\n    num_important_colors_used={},\n)'.format(A.width,A.height,A.num_color_planes,A.bits_per_pixel,CompressionType.to_str(A.compression_type),A.raw_bitmap_size,A.horizontal_resolution_ppm,A.vertical_resolution_ppm,A.num_colors_in_palette,A.num_important_colors_used)
	@staticmethod
	def from_positioned_file_handler(file_handler):
		C=file_handler;B=int.from_bytes(C.read(4),_B)
		if B<=0:raise ValueError('BMP header has invalid header size: '+str(B))
		elif B>100000:raise ValueError('BMP header looks like it may be too big (header_size='+str(B)+').')
		try:A=list(bytearray(C.read(B-4)))
		except MemoryError:raise MemoryError('MemoryError when trying to read BMP file header. header_size='+str(B))
		D=_A;E=_A;F=_A;G=_A;H=_A;I=_A;J=_A;K=_A;L=_A;M=_A
		if B in[40,52,56,108,124]or B>124:D=int.from_bytes(bytes(A[0:4]),_B);E=int.from_bytes(bytes(A[4:8]),_B);F=int.from_bytes(bytes(A[8:10]),_B);G=int.from_bytes(bytes(A[10:12]),_B);H=int.from_bytes(bytes(A[12:16]),_B);I=int.from_bytes(bytes(A[16:20]),_B);J=int.from_bytes(bytes(A[20:24]),_B);K=int.from_bytes(bytes(A[24:28]),_B);L=int.from_bytes(bytes(A[28:32]),_B);M=int.from_bytes(bytes(A[32:36]),_B)
		else:raise ValueError('BMP file looks like it might be using an old BMP DIB header that we do not support.')
		return DIBHeader(width=D,height=E,num_color_planes=F,bits_per_pixel=G,compression_type=H,raw_bitmap_size=I,horizontal_resolution_ppm=J,vertical_resolution_ppm=K,num_colors_in_palette=L,num_important_colors_used=M)
class BMPType:
	BM=0;BA=1;CI=2;CP=3;IC=4;PT=5
	@staticmethod
	def from_bytes(bmp_type_bytes):
		A=bytes(bmp_type_bytes).decode()
		if A=='BM':return BMPType.BM
		elif A=='BA':return BMPType.BA
		elif A=='CI':return BMPType.CI
		elif A=='CP':return BMPType.CP
		elif A=='IC':return BMPType.IC
		elif A=='PT':return BMPType.PT
		else:raise ValueError(f'Invalid BMP type: "{A}"')
class CompressionType:
	BI_RGB=0;BI_RLE8=1;BI_REL4=2;BI_BITFIELDS=3;BI_JPEG=4;BI_PNG=5;BI_ALPHABITFIELDS=6;BI_CMYK=11;BI_CMYKRLE8=12;BI_CMYKRLE4=13;STRINGS_DICT={0:'BI_RGB',1:'BI_RLE8',2:'BI_REL4',3:'BI_BITFIELDS',4:'BI_JPEG',5:'BI_PNG',6:'BI_ALPHABITFIELDS',11:'BI_CMYK',12:'BI_CMYKRLE8',13:'BI_CMYKRLE4'}
	@staticmethod
	def to_str(compression_type):A=compression_type;return CompressionType.STRINGS_DICT.get(A,str(A))
	@staticmethod
	def is_compressed(compression_type):return compression_type not in[CompressionType.BI_RGB,CompressionType.BI_CMYK]
