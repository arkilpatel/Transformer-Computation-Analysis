import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import copy
import time
from torch.autograd import Variable
import pdb


def clones(module, N):
	"Produce N identical layers."
	return nn.ModuleList([copy.deepcopy(module) for _ in range(N)])


class LayerNorm(nn.Module):
	"Construct a layernorm module (See citation for details)."

	def __init__(self, features, eps=1e-6):
		super(LayerNorm, self).__init__()
		self.a_2 = nn.Parameter(torch.ones(features))
		self.b_2 = nn.Parameter(torch.zeros(features))
		self.eps = eps

	def forward(self, x):
		mean = x.mean(-1, keepdim=True)
		std = x.std(-1, keepdim=True)
		return self.a_2 * (x - mean) / (std + self.eps) + self.b_2


class SublayerConnection(nn.Module):
	"""
	A residual connection followed by a layer norm.
	Note for code simplicity the norm is first as opposed to last.
	"""

	def __init__(self, size, dropout):
		super(SublayerConnection, self).__init__()
		self.norm = LayerNorm(size)
		self.dropout = nn.Dropout(dropout)

	def forward(self, x, sublayer):
		"Apply residual connection to any sublayer with the same size."
		return x + self.dropout(sublayer(self.norm(x)))


class SublayerConnectionWres(nn.Module):
	"""
	Not residual connection followed by a layer norm.
	Note for code simplicity the norm is first as opposed to last.
	"""

	def __init__(self, size, dropout):
		super(SublayerConnectionWres, self).__init__()
		self.norm = LayerNorm(size)
		self.dropout = nn.Dropout(dropout)

	def forward(self, x, sublayer):
		"Dont Apply residual connection to any sublayer with the same size."
		return self.dropout(sublayer(self.norm(x)))



def subsequent_mask(size):
	attn_shape = (1, size, size)
	subsequent_mask = np.triu(np.ones(attn_shape), k=1).astype('uint8')
	return torch.from_numpy(subsequent_mask) == 0


##### Postional Encoding #####


class PositionwiseFeedForward(nn.Module):
	def __init__(self, d_model, d_ff, dropout=0.1):
		super(PositionwiseFeedForward, self).__init__()
		self.w_1 = nn.Linear(d_model, d_ff)
		self.w_2 = nn.Linear(d_ff, d_model)
		self.dropout = nn.Dropout(dropout)

	def forward(self, x):
		return self.w_2(self.dropout(F.relu(self.w_1(x))))


class Embeddings(nn.Module):
	def __init__(self, d_model, vocab):
		super(Embeddings, self).__init__()
		self.lut = nn.Embedding(vocab, d_model)
		self.d_model = d_model

	def forward(self, x):
		return self.lut(x) * math.sqrt(self.d_model)


class PositionalEncoding(nn.Module):
	def __init__(self, d_model, dropout=0.1, max_len=5000):
		super(PositionalEncoding, self).__init__()
		self.dropout = nn.Dropout(p=dropout)

		pe = torch.zeros(max_len, d_model)
		position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
		div_term = torch.exp(torch.arange(
			0, d_model, 2, dtype=torch.float32) * -(math.log(10000.0) / float(d_model)))

		pe[:, 0::2] = torch.sin(position * div_term)
		pe[:, 1::2] = torch.cos(position * div_term)

		pe = pe.unsqueeze(0)
		self.register_buffer('pe', pe)

	def forward(self, x):
		x = x + Variable(self.pe[:, :x.size(1)], requires_grad=False)

		return self.dropout(x)


class NoPositionalEncoding(nn.Module):
	def __init__(self, d_model, dropout=0.1, max_len=5000):
		super(NoPositionalEncoding, self).__init__()
		self.dropout = nn.Dropout(p=dropout)

	def forward(self, x):
		x = x 

		return self.dropout(x)



'''Greedy Decode'''

def greedy_decode(model, src, src_mask, max_len, start_symbol, pad=0):
	#pdb.set_trace()
	memory = model.encode(src, src_mask)
	ys = torch.ones(memory.size(0), 1).fill_(start_symbol).type_as(src.data)
	for i in range(max_len-1):
		tgt_mask = (ys != pad).unsqueeze(-2)
		tgt_mask = tgt_mask & Variable(subsequent_mask(ys.size(-1)).type_as(tgt_mask.data))
		out = model.decode(memory, src_mask, 
						   Variable(ys), # tgt 
						   tgt_mask) 
		prob = model.generator(out[:, -1])
		_, next_word = torch.max(prob, dim = 1)
		# next_word = next_word.item()
		next_word = next_word.unsqueeze(1)
		ys = torch.cat([ys, next_word], dim=1)
	return ys