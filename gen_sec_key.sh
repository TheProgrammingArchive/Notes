if [! -f NotesApp/test.txt]; then
  touch test.txt
  op = $(openssl rand -hex 32)
  echo "SECRET_KEY='$op'" > test.txt
fi