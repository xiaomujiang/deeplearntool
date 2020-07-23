
from deeplearn.text_classification.dataprocess import readfile, cutword, stopword,savemodel,loadmodel
import gensim
import pandas as pd
import numpy as np
import xgboost as xgb
from tqdm import tqdm
from sklearn.svm import SVC
from keras.models import Sequential
from keras.layers.recurrent import LSTM, GRU
from keras.layers.core import Dense, Activation, Dropout
from keras.layers.embeddings import Embedding
from keras.layers.normalization import BatchNormalization
from keras.utils import np_utils
from sklearn import preprocessing, decomposition, model_selection, metrics, pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.naive_bayes import MultinomialNB
from keras.layers import GlobalMaxPooling1D, Conv1D, MaxPooling1D, Flatten, Bidirectional, SpatialDropout1D
from keras.preprocessing import sequence, text
from keras.callbacks import EarlyStopping
from nltk import word_tokenize

# 第一步读取数据
file_name = r'中文文本分类语料1.xlsx'
sheet_num = "sheet1"
data = readfile(file_name, sheet_num)
print(data.分类.unique())

# 第二步分词
name_head = "正文"  # 文本内容的字段名
data = cutword(data, name_head)
X = data['文本分词']
X = [i.split() for i in X]
print(X[:2])

model = gensim.models.Word2Vec(X,min_count =5,window =8,size=100)   # X是经分词后的文本构成的list，也就是tokens的列表的列表
embeddings_index = dict(zip(model.wv.index2word, model.wv.vectors))


print('Found %s word vectors.' % len(embeddings_index))
print(model['汽车'])

lbl_enc = preprocessing.LabelEncoder()
y = lbl_enc.fit_transform(data.分类.values)
xtrain, xvalid, ytrain, yvalid = train_test_split(data.文本分词.values, y,
                                                  stratify=y,
                                                  random_state=42,
                                                  test_size=0.1, shuffle=True)

# stop_file = '停用词汇总.txt'
# stwlist = stopword(stop_file)
# # 将语句转化为一个标准化的向量（Normalized Vector）
# def sent2vec(s):
#     import jieba
#     # jieba.enable_parallel() #并行分词开启
#     words = str(s).lower()
#     #words = word_tokenize(words)
#     words = jieba.lcut(words)
#     words = [w for w in words if not w in stwlist]
#     #words = [w for w in words if w.isalpha()]
#     M = []
#     for w in words:
#         try:
#             #M.append(embeddings_index[w])
#             M.append(model[w])
#         except:
#             continue
#     M = np.array(M)
#     v = M.sum(axis=0)
#     if type(v) != np.ndarray:
#         return np.zeros(300)
#     return v / np.sqrt((v ** 2).sum())
#
# # 对训练集和验证集使用上述函数，进行文本向量化处理
# xtrain_w2v = [sent2vec(x) for x in tqdm(xtrain)]
# xvalid_w2v = [sent2vec(x) for x in tqdm(xvalid)]
#
# xtrain_w2v = np.array(xtrain_w2v)
# xvalid_w2v = np.array(xvalid_w2v)

# 对标签进行binarize处理
ytrain_enc = np_utils.to_categorical(ytrain)
yvalid_enc = np_utils.to_categorical(yvalid)

# 使用 keras tokenizer
token = text.Tokenizer(num_words=None)
max_len = 70

token.fit_on_texts(list(xtrain) + list(xvalid))
xtrain_seq = token.texts_to_sequences(xtrain)
xvalid_seq = token.texts_to_sequences(xvalid)

#对文本序列进行zero填充
xtrain_pad = sequence.pad_sequences(xtrain_seq, maxlen=max_len)
xvalid_pad = sequence.pad_sequences(xvalid_seq, maxlen=max_len)

word_index = token.word_index

#基于已有的数据集中的词汇创建一个词嵌入矩阵（Embedding Matrix）
embedding_matrix = np.zeros((len(word_index) + 1, 100))
for word, i in tqdm(word_index.items()):
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        embedding_matrix[i] = embedding_vector


# 基于前面训练的Word2vec词向量，使用1个两层的LSTM模型
model = Sequential()
model.add(Embedding(len(word_index) + 1,
                     100,
                     weights=[embedding_matrix],
                     input_length=max_len,
                     trainable=False))
model.add(SpatialDropout1D(0.3))
model.add(LSTM(100, dropout=0.3, recurrent_dropout=0.3))

model.add(Dense(1024, activation='relu'))
model.add(Dropout(0.8))

model.add(Dense(1024, activation='relu'))
model.add(Dropout(0.8))

model.add(Dense(8))
model.add(Activation('softmax'))
model.compile(loss='categorical_crossentropy', optimizer='adam')


# model.fit(xtrain_pad, y=ytrain_enc, batch_size=512, epochs=1, verbose=1, validation_data=(xvalid_pad, yvalid_enc))
# 在模型拟合时，使用early stopping这个回调函数（Callback Function）
earlystop = EarlyStopping(monitor='val_loss', min_delta=0, patience=3, verbose=0, mode='auto')
model.fit(xtrain_pad, y=ytrain_enc, batch_size=512, epochs=5,
          verbose=1, validation_data=(xvalid_pad, yvalid_enc), callbacks=[earlystop])