# Minified from https://raw.githubusercontent.com/remixer-dec/mpy-img-decoder/refs/heads/master/PNGdecoder.py
# GPLv3 License, Copyright (C) 2020 Remixer Dec
# Usage: png('image.png', callback=lcd.drawPixel).render(x, y)
import zlib
from array import array
from io import BytesIO
def png(source,callback=print,cache=False,bg=(0,0,0),fastalpha=True):
	L=callback;A=0;E=0;C=4;X=[1,0,3,1,2,0,4];H=[];B=False;M=int;G=0;I=0;D=False;F=array('i');N=array('b',[-1,-1,-1])
	@micropython.viper
	def O(RGBlist)->int:A=RGBlist;return(int(A[0])<<16)+(int(A[1])<<8)+int(A[2])
	@micropython.viper
	def P(src,onlymeta=False):
		A=src;nonlocal D
		if isinstance(A,str):A=open(A,'rb')
		elif isinstance(A,bytes):A=BytesIO(A)
		C=A.read(8)
		if C!=b'\x89PNG\r\n\x1a\n':return
		while not D:
			S(A);U(A)
			if onlymeta:return B
			A.seek(4,1)
		A.close()
	@micropython.native
	def S(src):nonlocal A,E;A=J(src.read(4));E=src.read(4)
	@micropython.viper
	def J(inp)->int:return int(M.from_bytes(inp,'big'))
	@micropython.native
	def T(a,b):return a/b
	@micropython.viper
	def K(r:int,g:int,b:int,a:int):
		if fastalpha:return[r,g,b]if a!=0 else N
		if a==0:return N
		B=float(r);C=float(g);D=float(b);A=float(T(a,255));E=round(B*A+(1.-A)*float(bg[0]));F=round(C*A+(1.-A)*float(bg[1]));G=round(D*A+(1.-A)*float(bg[2]));return E,F,G
	@micropython.viper
	def U(src):
		B={b'IHDR':W,b'PLTE':Y,b'IDAT':d,b'IEND':V}
		if E in B:B[E](src)
		else:src.seek(A,1)
	def V(src):nonlocal D;D=True
	@micropython.native
	def W(src):A=src;nonlocal B;B=tuple(map(J,(A.read(4),A.read(4),A.read(1),A.read(1))));A.seek(3,1)
	@micropython.native
	def Y(src):
		nonlocal H
		for B in range(round(A//3)):H.append(src.read(3))
	@micropython.native
	def Z(c,d,w):A=c*d/8;B=round(A);C=round(A*w);return C,B
	@micropython.viper
	def Q(item,start,end):return item[start:end]
	@micropython.native
	def a(value):nonlocal C;C=value;return C
	@micropython.native
	def b(value):nonlocal A;A=value;return A
	@micropython.viper
	def c(x,y,c:int):
		if cache:F.append(c)
		if c>=0:L(x,y,c)
	@micropython.viper
	def d(src):
		E=src;L=True;P=b''
		while L:
			P+=E.read(A);E.seek(4,1);Y=J(E.read(4));L=bool(E.read(4)==b'IDAT')
			if not L:E.seek(12*-1,1)
			b(Y)
		H=zlib.decompress(P);H=BytesIO(H);S=int(B[0]);d=int(B[1]);D=int(B[2]);M=int(B[3]);f,g=Z(X[M],D,S);N=int(a(g));T=b'';h=(1<<D)-1
		for U in range(d):
			i=J(H.read(1));F=H.read(int(f));F=e(i,F,U,T)
			for C in range(S):
				if D>=8:V=O(R(Q(F,int(C)*int(N),int(C)*int(N)+int(N)),D,M))
				else:K=int(8//D);W=C//K+1*int(C%K!=0)-1*int(C!=0);j=Q(F,W,W+1);k=int(C==0)+C%K or K;l=int(j[0])>>8-D*k&h;V=O(R(l,D,M))
				c(int(G)+C,int(I)+U,V)
			T=F
	@micropython.viper
	def R(src,depth:int,colormode:int):
		I=colormode;C=depth;A=src
		if I==3:
			if not isinstance(A,M):L=int(A[0])
			else:L=int(A)
			D,E,F=H[L];return D,E,F
		if I==0:
			if C<=4:N=(1<<C)-1;J=round(int(A)*255//N);return J,J,J
			if C==8:B=A;return B,B,B
			if C==16:B,G=A;return K(B,B,B,G)
		if I==4:
			if C==8:B,G=A
			if C==16:B,S,G,O=A
			return K(B,B,B,G)
		if I==2:
			if C==8:D,E,F=A
			if C==16:D,P,E,Q,F,R=A
			return D,E,F
		if I==6:
			if C==8:D,E,F,G=A
			if C==16:D,P,E,Q,F,R,G,O=A
			return K(D,E,F,G)
	@micropython.native
	def e(f,row,y,prevrow):
		E=prevrow
		@micropython.viper
		def G(a:int,b:int,c:int)->int:
			A=a+b-c;C=abs(A-a);D=abs(A-b);E=abs(A-c)
			if C<=D and C<=E:B=a
			elif D<=E:B=b
			else:B=c
			return B
		@micropython.native
		def A(c:int)->int:return D[c-int(C)]if c>=int(C)else 0
		@micropython.native
		def B(r:int,c:int)->int:return E[c]if r>0 else 0
		@micropython.native
		def H(r:int,c:int)->int:return E[c-int(C)]if r>0 and c>=int(C)else 0
		@micropython.viper
		def I(x,r,c):return x
		@micropython.viper
		def J(x,r,c)->int:return int(x+A(c))
		@micropython.viper
		def K(x,r,c)->int:return int(x+B(r,c))
		@micropython.viper
		def L(x:int,r,c)->int:return int(x+int(A(c)+B(r,c))//2)
		@micropython.viper
		def M(x:int,r,c)->int:return x+int(G(A(c),B(r,c),H(r,c)))
		N=[I,J,K,L,M];D=array('B')
		if f>=0 and f<5:
			for F in range(len(row)):D.append(N[f](row[F],y,F)&255)
		return D
	@micropython.native
	def f():
		A=0;C,D,J,K=B
		for E in range(D):
			for H in range(C):
				if F[A]>=0:L(G+H,I+E,F[A])
				A+=1
	class g:
		def __init__(A):A.file=source
		def getMeta(A):return B or P(A.file,True)
		def checkAndRender(A,w=False,h=False,wxh=False,**D):
			B,C,E,F=A.getMeta()
			if w and B>w:return
			if h and C>h:return
			if wxh and B*C>wxh:return
			A.render(**D)
		@micropython.native
		def render(self,x=0,y=0,placeholder=False,phcolor=12303291):
			B=placeholder;A=self;nonlocal G,I,D,H;G=x;I=y
			if not F:
				H=[];D=False
				if B:C,E,J,K=A.getMeta();B(x,y,C,E,phcolor)
				P(A.file,False)
			else:f()
			return A
	return g()
