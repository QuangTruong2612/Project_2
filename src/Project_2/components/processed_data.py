import pandas as pd
from pyvi import ViTokenizer
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from Project_2.entity.config_entity import ProcessedDataConfigure

class ProcessedData:
    def __init__(self, config = ProcessedDataConfigure):
        self.config = config
        self.stopwords = {
                            'thì', 'là', 'mà', 'và', 'của', 'những', 'các', 'cái', 'việc', 'bị', 'bởi',
                            'shop', 'sản_phẩm', 'hàng', 'giao', 'mua', 'bán', 'mình', 'tiki', 'shopee',
                            'nhé', 'nha', 'ạ', 'ơi', 'nhen', 'kaka', 'hihi'
                        }

        self.teencode = {
                        'k': 'không', 'ko': 'không', 'kh': 'không', 'hok': 'không',
                        'dc': 'được', 'đc': 'được',
                        'bt': 'bình thường',
                        'wa': 'quá',
                        'uk': 'ừ',
                        'z': 'vậy',
                        'sp': 'sản phẩm'
                    }

        self.vectorizer = TfidfVectorizer(
                                            ngram_range=self.config.ngram,
                                            max_features=self.config.max_features,
                                            min_df=self.config.min_df # Bỏ qua những từ xuất hiện quá ít (dưới 2 lần)
                                        )

    def load_data(self) -> pd.DataFrame:
        try:
            path = self.config.data_path
            data = pd.read_csv(path)
            print("Load data completed!")
            return data
        except Exception as e:
            print(f"Error: {e}")
            raise e

    # Droip columns not use in training. You can change cols in params
    def drop_cols_not_use(self, data: pd.DataFrame) -> pd.DataFrame:
        try:
            data = data.drop(self.config.cols_not_use, axis=1)
            print("Drop columns not use in training !")
            return data
        except Exception as e:
            print(f"Error: {e}")
            raise e

    # clean text
    def clean_text(self, text : str) -> None:
        # lower
        text = text.lower()

        # remove emoji
        emoji_pattern  = re.compile(
                                    u"[\U0001F600-\U0001F64F"  # Emoticons (Mặt cười...)
                                    u"\U0001F300-\U0001F5FF"  # Symbols & Pictographs
                                    u"\U0001F680-\U0001F6FF"  # Transport & Map
                                    u"\U0001F900-\U0001F9FF"  # Supplemental Symbols (Các emoji mới)
                                    u"\u2600-\u26FF"          # Misc Symbols (Dấu tim, quân bài...)
                                    u"\u2700-\u27BF"          # Dingbats
                                    u"\u200D\uFE0F]+"         # Zero-width joiner (cho các emoji ghép)
                                )

        text = emoji_pattern.sub(r'', text)
        # remove special text
        text = re.sub(r'[^\w\s,.!?]', '', text)
        text = re.sub(r'[.,!?;:]', '', text)

        # processed teen code
        words = text.split()
        words = [self.teencode.get(word, word) for word in words]
        text = ' '.join(words)

        text_tokenized = ViTokenizer.tokenize(text)

        tokens = text_tokenized.split()
        clean_tokens = [t for t in tokens if t not in self.stopwords]

        return ' '.join(clean_tokens)

    def split_data(self, data: pd.DataFrame) -> tuple:
        try:
            X = data["content"].tolist()
            y = data[self.config.target].tolist()

            X_train, X_test, y_train, y_test = train_test_split(
                                                                X, y,
                                                                test_size=self.config.test_size,
                                                                random_state=self.config.random_state,
                                                                stratify=y
                                                            )
            print("Split data completed!")
            return X_train, X_test, y_train, y_test
        except Exception as e:
            print(f"Error: {e}")
            raise e

    def save_data(self, X_train, X_test, y_train, y_test) -> None:
        try:
            train_data = pd.DataFrame({ "content": X_train, self.config.target: y_train })
            test_data = pd.DataFrame({ "content": X_test, self.config.target: y_test })

            train_data.to_csv(self.config.train_path, index=False)
            test_data.to_csv(self.config.test_path, index=False)

            print(f"Save data completed! \nTrain path: {self.config.train_path} \nTest path: {self.config.test_path}")
        except Exception as e:
            print(f"Error: {e}")
            raise e

        # process data
    def process_data(self, data: pd.DataFrame) -> None:
        try:
            # drop cols
            data = self.drop_cols_not_use(data)

            # check null
            print(f"Check Null in data : {data.isnull().sum()}")
            data = data.dropna()

            # check duplicated
            print(f"Check Duplicated in data : {data.duplicated().sum()}")
            data = data.drop_duplicates()

            # clean text
            data["content"] = data["content"].apply(self.clean_text)
            print("Process data completed!")

            X_train, X_test, y_train, y_test = self.split_data(data)
            self.save_data(X_train, X_test, y_train, y_test)


        except Exception as e:
            print(f"Error: {e}")
            raise e
