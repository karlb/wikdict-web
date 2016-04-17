wget http://download.wikdict.com/dictionaries/sqlite/1/all.tar.gz -O data/all.tar.gz
mkdir -p data/dict && tar xvfz data/all.tar.gz --directory data/dict && rm data/all.tar.gz
