# 팀 공동 작업

처음 내려받기:
```
git clone https://github.com/inexist0000/algo.git
cd algo
python utill.py
```

지도는 assets/map.png를 자동으로 읽습니다. 노드 추가 모드에서 클릭하고 이름만 입력하세요. 높이는 기본 0m이며 오른쪽에서 좌표와 함께 수정할 수 있습니다. Ctrl+S로 저장합니다.

수정 전 편집기를 닫고 최신 버전을 받으세요. 자신의 브랜치 이름을 사용하세요.
```
git pull --ff-only
git switch -c my-change
```

편집하고 저장한 뒤:
```
git add .
git commit -m "Update map graph"
git push -u origin my-change
```

GitHub에서 Pull Request를 만들어 합칩니다. graph.json은 동시에 수정하면 충돌할 수 있으므로 차례로 편집하세요. 브랜치를 바꾸거나 최신 버전을 받기 전에 편집기를 닫으세요.
