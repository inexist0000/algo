"""Read the saved undirected graph and find a shortest path with Dijkstra."""
import heapq
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data' / 'graph.json'


def load_graph(path=DATA):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    nodes = {node['id']: node for node in data['nodes']}
    if len(nodes) != len(data['nodes']):
        raise ValueError('중복된 노드 ID가 있습니다.')
    adjacency = {node_id: [] for node_id in nodes}
    units = set()
    for edge in data['edges']:
        source, target = edge['source'], edge['target']
        if source not in nodes or target not in nodes:
            raise ValueError('엣지가 존재하지 않는 노드를 참조합니다.')
        weight = float(edge['weight'])
        if not math.isfinite(weight) or weight < 0:
            raise ValueError('Dijkstra 가중치는 0 이상의 유한한 숫자여야 합니다.')
        units.add(edge.get('weight_unit', data.get('weight_unit', 'unknown')))
        adjacency[source].append((target, weight))
        adjacency[target].append((source, weight))
    if len(units) > 1:
        raise ValueError('초와 픽셀 등 서로 다른 가중치 단위가 섞여 있습니다. 편집기 데이터의 단위를 먼저 통일하세요.')
    return nodes, adjacency, next(iter(units), data.get('weight_unit', 'unknown'))


def dijkstra(adjacency, start, goal):
    if start not in adjacency or goal not in adjacency:
        raise ValueError('시작점 또는 도착점이 존재하지 않습니다.')
    distances = {start: 0.0}
    previous = {}
    queue = [(0.0, start)]
    while queue:
        distance, current = heapq.heappop(queue)
        if distance != distances.get(current):
            continue
        if current == goal:
            path = [goal]
            while path[-1] != start:
                path.append(previous[path[-1]])
            return distance, path[::-1]
        for neighbor, weight in adjacency[current]:
            candidate = distance + weight
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                previous[neighbor] = current
                heapq.heappush(queue, (candidate, neighbor))
    return math.inf, []


def choose_node(nodes, prompt):
    while True:
        value = input(prompt).strip()
        if value in nodes:
            return value
        matches = [key for key, node in nodes.items() if node['name'] == value]
        if len(matches) == 1:
            return matches[0]
        print('노드 ID를 입력하세요.' if len(matches) > 1 else '해당 노드가 없습니다. 이름 또는 ID를 다시 입력하세요.')


def main():
    try:
        nodes, adjacency, unit = load_graph()
        if not nodes:
            print('저장된 노드가 없습니다. utill.py에서 먼저 그래프를 만들고 저장하세요.')
            return
        print('사용 가능한 노드:')
        for node_id, node in nodes.items():
            print(f"  {node_id}: {node['name']}")
        start = choose_node(nodes, '\n시작점 이름 또는 ID: ')
        goal = choose_node(nodes, '도착점 이름 또는 ID: ')
        distance, path = dijkstra(adjacency, start, goal)
        if not path:
            print('두 지점을 연결하는 경로가 없습니다.')
            return
        print('\n최단 경로: ' + ' → '.join(nodes[key]['name'] for key in path))
        print('노드 ID: ' + ' → '.join(path))
        print(f'총 가중치: {distance:g} ({unit})')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'그래프를 처리할 수 없습니다: {exc}')
    except (EOFError, KeyboardInterrupt):
        print('\n종료합니다.')


if __name__ == '__main__':
    main()
