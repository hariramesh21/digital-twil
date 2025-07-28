from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import random
from flask_socketio import SocketIO
import threading
import time
from math import pi

app = Flask(__name__)
socketio = SocketIO(app)
pcs_data = []

def initialize_pcs():
    global pcs_data
    pcs_data = []

    all_pc_ids = [f'PC-{str(i).zfill(2)}' for i in range(1, 21)]

    num_conflicts = random.randint(2, 2)
    conflict_pc_ids = random.sample(all_pc_ids, num_conflicts)
    
    for i in range(1, 21):
        pc_id = f'PC-{str(i).zfill(2)}'
        status = 'active'

        if pc_id in conflict_pc_ids:
            status = 'conflict'
        elif i <= 10:
            status = 'active'
        elif i <= 17:
            status = 'user'
        else:
            status = 'backup'

        if i <= 10:
            pc_x = (i - 1) * 3.0 - 13.5
            pc_z = -4.0
        else:
            pc_x = (i - 11) * 3.0 - 13.5
            pc_z = 4.0

        pc = {
            'id': pc_id,
            'status': status,
            'cpu': random.randint(20, 60),
            'ram': random.randint(30, 80),
            'disk': random.randint(15, 45),
            'last_updated': datetime.now().strftime('%H:%M:%S'),
            'position': i - 1,
            'location': f'Row-{(i - 1) // 10 + 1}, Seat-{(i - 1) % 10 + 1}',
            'x': pc_x,
            'y': 0,
            'z': pc_z
        }
        pcs_data.append(pc)

initialize_pcs()

def emit_pc_update(pc_id=None):
    if pc_id:
        pc = next((p for p in pcs_data if p['id'] == pc_id), None)
        if pc:
            socketio.emit('pc_update', {'pc': pc})
    else:
        socketio.emit('pcs_refresh', {'pcs': pcs_data})

@app.route('/')
def replica_view():
    return render_3d_template("Main 3D Lab", show_controls=False)

@app.route('/control')
def main_3d_view():
    return render_3d_template("Control Panel", show_controls=True)

conflicts = {}

def resolve_conflict(pc):
    pc_id = pc['id']
    if pc_id in conflicts:
        del conflicts[pc_id]
    else:
        pass

def render_3d_template(title, show_controls):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ margin: 0; overflow: hidden; font-family: Arial, sans-serif; }}
            #info {{
                position: absolute;
                top: 10px;
                width: 100%;
                text-align: center;
                color: white;
                background-color: rgba(0,0,0,0.7);
                padding: 10px;
                z-index: 100;
            }}
            #stats {{
                position: absolute;
                top: 60px;
                left: 10px;
                background-color: rgba(0,0,0,0.7);
                color: white;
                padding: 10px;
                border-radius: 5px;
                z-index: 100;
            }}
            #controls {{
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background-color: rgba(0,0,0,0.7);
                color: white;
                padding: 10px;
                border-radius: 5px;
                z-index: 100;
                display: flex;
                gap: 10px;
                display: {'block' if show_controls else 'none'};
            }}
            button {{
                padding: 8px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            button:hover {{ background-color: #45a049; }}
            #pc-details {{
                position: absolute;
                top: 60px;
                right: 10px;
                background-color: rgba(0,0,0,0.8);
                color: white;
                padding: 15px;
                border-radius: 8px;
                z-index: 100;
                max-width: 300px;
                display: none;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                border: 1px solid rgba(255,255,255,0.2);
            }}
            #pc-details h3 {{
                margin-top: 0;
                color: #ADD8E6;
                border-bottom: 1px solid rgba(255,255,255,0.3);
                padding-bottom: 5px;
                margin-bottom: 10px;
            }}
            #pc-details div {{
                margin-bottom: 8px;
            }}
            .progress-bar {{
                width: 100%;
                background-color: #444;
                border-radius: 4px;
                margin: 5px 0;
                height: 20px;
                overflow: hidden;
            }}
            .progress-fill {{
                height: 100%;
                border-radius: 4px;
                text-align: right;
                padding-right: 5px;
                box-sizing: border-box;
                font-weight: bold;
                line-height: 20px;
                color: white;
            }}
            .cpu-fill {{ background-color: #e74c3c; }}
            .ram-fill {{ background-color: #3498db; }}
            .disk-fill {{ background-color: #27ae60; }}
        </style>
    </head>
    <body>
        <div id="info">
            {title} | <a href="/{'control' if not show_controls else ''}" style="color: white;">
                Switch to {'Control Panel' if not show_controls else 'Main 3D Lab'}
            </a>
        </div>

        <div id="stats">
            Active: <span id="active-count">0</span> |
            In Use: <span id="user-count">0</span> |
            Conflicts: <span id="conflict-count">0</span>
        </div>

        <div id="pc-details">
            <h3 id="pc-title">PC Details</h3>
            <div id="pc-status"></div>
            <div id="pc-location"></div>
            <div id="pc-last-updated"></div>

            <div>CPU: <span id="pc-cpu-val">0</span>%</div>
            <div class="progress-bar"><div id="cpu-bar" class="progress-fill cpu-fill" style="width: 0%"></div></div>

            <div>RAM: <span id="pc-ram-val">0</span>%</div>
            <div class="progress-bar"><div id="ram-bar" class="progress-fill ram-fill" style="width: 0%"></div></div>

            <div>Disk: <span id="pc-disk-val">0</span>%</div>
            <div class="progress-bar"><div id="disk-bar" class="progress-fill disk-fill" style="width: 0%"></div></div>

            <div id="pc-actions" style="margin-top: 10px;"></div>
            <button onclick="closeDetails()" style="margin-top: 10px; width: 100%;">Close</button>
        </div>

        <div id="controls">
            <button onclick="resetCamera()">Reset View</button>
            <button onclick="toggleGrid()">Toggle Grid</button>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>

        <script>
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0xADD8E6);

            const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(20, 15, 25);

            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.shadowMap.enabled = true;
            document.body.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.target.set(0, 0.5, 0);
            controls.update();

            const ambientLight = new THREE.AmbientLight(0x404040);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(10, 20, 10);
            directionalLight.castShadow = true;
            scene.add(directionalLight);

            const floorWidth = 30;
            const floorDepth = 30;
            const floorGeometry = new THREE.PlaneGeometry(floorWidth, floorDepth);
            const floorMaterial = new THREE.MeshPhongMaterial({{ color: 0xAAAAAA }});
            const floor = new THREE.Mesh(floorGeometry, floorMaterial);
            floor.rotation.x = -Math.PI / 2;
            floor.receiveShadow = true;
            scene.add(floor);

            const gridHelper = new THREE.GridHelper(floorWidth, 30, 0xCCCCCC, 0x999999);
            gridHelper.position.y = 0.01;
            scene.add(gridHelper);

            const wallHeight = 8;
            const wallMaterial = new THREE.MeshPhongMaterial({{ color: 0xF0F0F0 }});
            const wallThickness = 0.2;
            
            const frontWallGeometry = new THREE.BoxGeometry(floorWidth, wallHeight, wallThickness);
            const frontWall = new THREE.Mesh(frontWallGeometry, wallMaterial);
            frontWall.position.set(0, wallHeight / 2, -floorDepth / 2 - wallThickness / 2);
            frontWall.receiveShadow = true;
            scene.add(frontWall);

            const doorWidth = 3;
            const doorHeight = 4;
            const wallSegmentWidth = (floorWidth - doorWidth) / 2;

            const backWallLeftGeometry = new THREE.BoxGeometry(wallSegmentWidth, wallHeight, wallThickness);
            const backWallLeft = new THREE.Mesh(backWallLeftGeometry, wallMaterial);
            backWallLeft.position.set(-wallSegmentWidth / 2 - doorWidth / 2, wallHeight / 2, floorDepth / 2 + wallThickness / 2);
            backWallLeft.receiveShadow = true;
            scene.add(backWallLeft);

            const backWallRightGeometry = new THREE.BoxGeometry(wallSegmentWidth, wallHeight, wallThickness);
            const backWallRight = new THREE.Mesh(backWallRightGeometry, wallMaterial);
            backWallRight.position.set(wallSegmentWidth / 2 + doorWidth / 2, wallHeight / 2, floorDepth / 2 + wallThickness / 2);
            backWallRight.receiveShadow = true;
            scene.add(backWallRight);

            const doorGroup = new THREE.Group();
            doorGroup.position.set(-doorWidth / 2, 0, floorDepth / 2 + wallThickness / 2);
            doorGroup.rotation.y = -Math.PI / 4; 

            const doorGeometry = new THREE.BoxGeometry(doorWidth, doorHeight, wallThickness * 1.1);
            const doorMaterial = new THREE.MeshPhongMaterial({{ color: 0x964B00 }});
            const door = new THREE.Mesh(doorGeometry, doorMaterial);
            door.position.set(doorWidth / 2, doorHeight / 2, 0); 
            door.receiveShadow = true;
            doorGroup.add(door);
            scene.add(doorGroup);

            const leftWallGeometry = new THREE.BoxGeometry(wallThickness, wallHeight, floorDepth + 2 * wallThickness);
            const leftWall = new THREE.Mesh(leftWallGeometry, wallMaterial);
            leftWall.position.set(-floorWidth / 2 - wallThickness / 2, wallHeight / 2, 0);
            leftWall.receiveShadow = true;
            scene.add(leftWall);

            const rightWallGeometry = new THREE.BoxGeometry(wallThickness, wallHeight, floorDepth + 2 * wallThickness);
            const rightWall = new THREE.Mesh(rightWallGeometry, wallMaterial);
            rightWall.position.set(floorWidth / 2 + wallThickness / 2, wallHeight / 2, 0);
            rightWall.receiveShadow = true;
            scene.add(rightWall);
            
            const ceilingGeometry = new THREE.PlaneGeometry(floorWidth, floorDepth);
            const ceilingMaterial = new THREE.MeshPhongMaterial({{ color: 0xE0E0E0, side: THREE.DoubleSide }});
            const ceiling = new THREE.Mesh(ceilingGeometry, ceilingMaterial);
            ceiling.rotation.x = Math.PI / 2;
            ceiling.position.y = wallHeight;
            ceiling.receiveShadow = true;
            scene.add(ceiling);

            const screenWidth = 8;
            const screenHeight = 4.5;
            const screenGeometry = new THREE.PlaneGeometry(screenWidth, screenHeight);
            const screenMaterial = new THREE.MeshBasicMaterial({{ color: 0xFFFFFF, side: THREE.DoubleSide }});
            const projectorScreen = new THREE.Mesh(screenGeometry, screenMaterial);
            const screenY = wallHeight * 0.6;
            projectorScreen.position.set(0, screenY, -floorDepth / 2 + wallThickness * 0.51); 
            scene.add(projectorScreen);
            
            const projectorHeight = 0.3;
            const projectorStandHeight = screenY - (projectorHeight / 2) - 0.15;
            const projectorStandGeometry = new THREE.BoxGeometry(0.5, projectorStandHeight, 0.5);
            const projectorStandMaterial = new THREE.MeshPhongMaterial({{ color: 0x888888 }});
            const projectorStand = new THREE.Mesh(projectorStandGeometry, projectorStandMaterial);
            projectorStand.position.set(0, projectorStandHeight / 2, 9);
            projectorStand.castShadow = true;
            scene.add(projectorStand);
            
            const projectorGeometry = new THREE.BoxGeometry(1.0, projectorHeight, 1.2);
            const projectorMaterial = new THREE.MeshPhongMaterial({{ color: 0x333333 }});
            const projector = new THREE.Mesh(projectorGeometry, projectorMaterial);
            projector.position.set(0, projectorStandHeight + projectorHeight / 2, 9);
            projector.castShadow = true;
            scene.add(projector);

            const pcMaterials = {{
                'active': new THREE.MeshPhongMaterial({{ color: 0x4CAF50 }}),
                'user': new THREE.MeshPhongMaterial({{ color: 0x2196F3 }}),
                'conflict': new THREE.MeshPhongMaterial({{ color: 0xf44336 }}),
                'backup': new THREE.MeshPhongMaterial({{ color: 0xFFC107 }}),
                'inactive': new THREE.MeshPhongMaterial({{ color: 0x555555 }})
            }};

            const pcMeshes = {{}};
            const pcs = [
                // Front row 1
                {{ id: 'pc_1', status: 'active', x: -2.5, z: 5.0, location: 'Row A, Seat 1', cpu: 15, ram: 30, disk: 45 }},
                {{ id: 'pc_2', status: 'user', x: 7.5, z: 5.0, location: 'Row A, Seat 2', cpu: 75, ram: 60, disk: 80 }},

                // Front row 2
                {{ id: 'pc_3', status: 'active', x: -7.5, z: -5.0, location: 'Row B, Seat 1', cpu: 20, ram: 40, disk: 50 }},
                {{ id: 'pc_4', status: 'active', x: 7.5, z: -5.0, location: 'Row B, Seat 2', cpu: 30, ram: 50, disk: 60 }},
                
                // Back row 1
                {{ id: 'pc_5', status: 'user', x: -7.5, z: 0.0, location: 'Row C, Seat 1', cpu: 85, ram: 70, disk: 90 }},
                {{ id: 'pc_6', status: 'conflict', x: -2.5, z: 0.0, location: 'Row C, Seat 2', cpu: 95, ram: 80, disk: 95 }},
                {{ id: 'pc_7', status: 'active', x: 2.5, z: 0.0, location: 'Row C, Seat 3', cpu: 10, ram: 25, disk: 30 }},
                {{ id: 'pc_8', status: 'active', x: 7.5, z: 0.0, location: 'Row C, Seat 4', cpu: 25, ram: 35, disk: 40 }},
                
                // Back row 2
                {{ id: 'pc_9', status: 'user', x: -7.5, z: 5.0, location: 'Row D, Seat 1', cpu: 60, ram: 55, disk: 70 }},
                {{ id: 'pc_10', status: 'active', x: -2.5, z: -5.0, location: 'Row D, Seat 2', cpu: 20, ram: 30, disk: 25 }},
                {{ id: 'pc_11', status: 'user', x: 2.5, z: -5.0, location: 'Row D, Seat 3', cpu: 70, ram: 65, disk: 85 }},
                {{ id: 'pc_13', status: 'backup', x: 2.5, z: 5.0, location: 'Storage', cpu: 5, ram: 10, disk: 20, last_updated: 'N/A' }}
            
            ];
            
            function renderAllPCs() {{

                const deskWidth = 2.5;
                const deskHeight = 0.9;
                const deskDepth = 1.5;
                const pcTowerWidth = 0.3;
                const pcTowerHeight = 0.8;
                const pcTowerDepth = 0.8;
                const monitorWidth = 1.2;
                const monitorHeight = 0.9;
                const monitorDepth = 0.1;

                pcs.forEach(pc => {{
                    const group = new THREE.Group();
                    group.position.set(pc.x, 0, pc.z);
                    group.userData.pcId = pc.id;

                    const deskGeometry = new THREE.BoxGeometry(deskWidth, deskHeight, deskDepth);
                    const deskMaterial = new THREE.MeshPhongMaterial({{ color: 0xCC7722 }});
                    const desk = new THREE.Mesh(deskGeometry, deskMaterial);
                    desk.position.y = deskHeight / 2;
                    desk.castShadow = true;
                    group.add(desk);

                    const baseGeometry = new THREE.BoxGeometry(pcTowerWidth, pcTowerHeight, pcTowerDepth);
                    const base = new THREE.Mesh(baseGeometry, pcMaterials[pc.status]);
                    base.position.set(-deskWidth / 2 - pcTowerWidth / 2 - 0.1, pcTowerHeight / 2, 0);
                    base.castShadow = true;
                    group.add(base);

                    const monitorGeometry = new THREE.BoxGeometry(monitorWidth, monitorHeight, monitorDepth);
                    const monitor = new THREE.Mesh(monitorGeometry, new THREE.MeshPhongMaterial({{ color: 0x333333 }}));
                    monitor.position.set(0, deskHeight + monitorHeight / 2, -deskDepth / 2 + monitorDepth / 2 + 0.1);
                    monitor.castShadow = true;
                    group.add(monitor);

                    const screenGeometry = new THREE.PlaneGeometry(monitorWidth * 0.8, monitorHeight * 0.8);
                    const screenMaterial = new THREE.MeshBasicMaterial({{
                        color: pc.status === 'conflict' ? 0xff0000 : (pc.status === 'inactive' || pc.status === 'backup' ? 0x000000 : 0x000000),
                        side: THREE.DoubleSide
                    }});
                    const screen = new THREE.Mesh(screenGeometry, screenMaterial);
                    screen.position.set(
                        monitor.position.x,
                        monitor.position.y,
                        monitor.position.z + monitorDepth / 2 + 0.01
                    );
                    group.add(screen);

                    scene.add(group);
                    pcMeshes[pc.id] = group;
                }});
            }}

            function updatePCMesh(pc) {{
                const group = pcMeshes[pc.id];
                if (group) {{
                    const base = group.children.find(
                        child => child.geometry.type === 'BoxGeometry' && child.position.x < 0
                    );
                    const screen = group.children.find(
                        child => child.type === 'Mesh' && child.geometry.type === 'PlaneGeometry'
                    );

                    if (base) {{
                        base.material = pcMaterials[pc.status];
                    }}
                    if (screen) {{
                        screen.material.color.set(pc.status === 'conflict' ? 0xff0000 : (pc.status === 'inactive' || pc.status === 'backup' ? 0x000000 : 0x000000));
                    }}
                }}
            }}

            function updateStats() {{
                const active = pcs.filter(pc => pc.status === 'active').length;
                const user = pcs.filter(pc => pc.status === 'user').length;
                const conflict = pcs.filter(pc => pc.status === 'conflict').length;
                const backup = pcs.filter(pc => pc.status === 'backup').length;
                const inactive = pcs.filter(pc => pc.status === 'inactive').length; 


                document.getElementById('active-count').textContent = active;
                document.getElementById('user-count').textContent = user;
                document.getElementById('conflict-count').textContent = conflict;
            }}

            function showPCDetails(pcId) {{
                const pc = pcs.find(p => p.id === pcId);
                if (!pc) return;

                selectedPc = pc;
                const details = document.getElementById('pc-details');
                const actionsDiv = document.getElementById('pc-actions');
                actionsDiv.innerHTML = '';

                document.getElementById('pc-title').textContent = pc.id;
                document.getElementById('pc-status').textContent = `Status: ${{pc.status.toUpperCase()}}`;
                document.getElementById('pc-location').textContent = `Location: ${{pc.location}}`;
                document.getElementById('pc-last-updated').textContent = `Updated: ${{pc.last_updated}}`;

                document.getElementById('pc-cpu-val').textContent = pc.cpu;
                document.getElementById('cpu-bar').style.width = `${{pc.cpu}}%`;
                document.getElementById('cpu-bar').textContent = `${{pc.cpu}}%`;

                document.getElementById('pc-ram-val').textContent = pc.ram;
                document.getElementById('ram-bar').style.width = `${{pc.ram}}%`;
                document.getElementById('ram-bar').textContent = `${{pc.ram}}%`;

                document.getElementById('pc-disk-val').textContent = pc.disk;
                document.getElementById('disk-bar').style.width = `${{pc.disk}}%`;
                document.getElementById('disk-bar').textContent = `${{pc.disk}}%`;

                if ({'true' if show_controls else 'false'}) {{
                    if (pc.status === 'conflict') {{
                        actionsDiv.innerHTML += `<button onclick="performPCAction('${{pc.id}}', 'resolve')">Resolve Conflict</button>`;
                    }} else if (pc.status === 'active') {{
                        actionsDiv.innerHTML += `<button onclick="performPCAction('${{pc.id}}', 'assign')">Assign</button>`;
                        actionsDiv.innerHTML += `<button onclick="performPCAction('${{pc.id}}', 'restart')">Restart</button>`;
                    }} else if (pc.status === 'user') {{
                        actionsDiv.innerHTML += `<button onclick="performPCAction('${{pc.id}}', 'release')">Release</button>`;
                        actionsDiv.innerHTML += `<button onclick="performPCAction('${{pc.id}}', 'restart')">Restart</button>`;
                    }} else if (pc.status === 'inactive' || pc.status === 'backup') {{
                        actionsDiv.innerHTML += `<button onclick="performPCAction('${{pc.id}}', 'restart')">Restart</button>`;
                    }}
                    
                    if (pc.status !== 'backup' && pc.status !== 'inactive') {{
                        actionsDiv.innerHTML += `<button onclick="performPCAction('${{pc.id}}', 'shutdown')" style="background-color: #f44336;">Shutdown</button>`;
                    }}
                }}
                
                details.style.display = 'block';
            }}

            function closeDetails() {{
                document.getElementById('pc-details').style.display = 'none';
                selectedPc = null;
            }}

            function performPCAction(pcId, action) {{
                fetch(`/api/pcs/${{pcId}}/action`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{ action: action }}),
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        console.log(data.message);
                    }} else {{
                        alert('Error performing action: ' + data.message);
                    }}
                }})
                .catch(error => console.error('Error:', error));
            }}

            function refreshAllPCs() {{
                fetch('/api/pcs/refresh', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        console.log(data.message);
                    }} else {{
                        alert('Error refreshing PCs: ' + data.message);
                    }}
                }})
                .catch(error => console.error('Error:', error));
            }}

            if ({'true' if show_controls else 'false'}) {{
                const controlsDiv = document.getElementById('controls');
                const refreshButton = document.createElement('button');
                refreshButton.textContent = 'Refresh All PCs';
                refreshButton.onclick = refreshAllPCs;
                controlsDiv.appendChild(refreshButton);
            }}

            function resetCamera() {{
                camera.position.set(20, 15, 25);
                controls.target.set(0, 0.5, 0);
                controls.update();
            }}

            function toggleGrid() {{
                gridHelper.visible = !gridHelper.visible;
            }}

            function onMouseClick(event) {{
                const mouse = new THREE.Vector2(
                    (event.clientX / window.innerWidth) * 2 - 1,
                    -(event.clientY / window.innerHeight) * 2 + 1
                );

                const raycaster = new THREE.Raycaster();
                raycaster.setFromCamera(mouse, camera);

                const intersects = raycaster.intersectObjects(Object.values(pcMeshes), true);

                if (intersects.length > 0) {{
                    let obj = intersects[0].object;
                    while (obj.parent && !obj.userData.pcId) {{
                        obj = obj.parent;
                    }}
                    if (obj.userData.pcId) {{
                        showPCDetails(obj.userData.pcId);
                    }}
                }}
            }}

            function onWindowResize() {{
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            }}

            function animate() {{
                requestAnimationFrame(animate);
                controls.update();

                Object.values(pcMeshes).forEach(pcMesh => {{
                    const pc = pcs.find(p => p.id === pcMesh.userData.pcId);
                    if (pc && pc.status === 'conflict') {{
                        const screen = pcMesh.children.find(
                            child => child.type === 'Mesh' && child.geometry.type === 'PlaneGeometry'
                        );
                        if (screen) {{
                            const intensity = 0.5 + 0.5 * Math.sin(Date.now() * 0.005);
                            screen.material.color.setRGB(intensity, 0, 0);
                        }}
                    }} else if (pc && pc.status === 'inactive' || pc.status === 'backup') {{
                        const screen = pcMesh.children.find(
                            child => child.type === 'Mesh' && child.geometry.type === 'PlaneGeometry'
                        );
                        if (screen) {{
                            screen.material.color.set(0x000000);
                        }}
                    }} else {{
                        const screen = pcMesh.children.find(
                            child => child.type === 'Mesh' && child.geometry.type === 'PlaneGeometry'
                        );
                        if (screen) {{
                             screen.material.color.set(0x000000);
                        }}
                    }}
                }});

                renderer.render(scene, camera);
            }}

            window.addEventListener('click', onMouseClick, false);
            window.addEventListener('resize', onWindowResize, false);

            fetch('/api/pcs')
                .then(response => response.json())
                .then(data => {{
                    pcs = data;
                    renderAllPCs();
                    updateStats();
                }})
                .catch(error => {{
                    console.error('Error fetching initial PC data:', error);
                    renderAllPCs();
                    updateStats();
                }});

            animate();
        </script>
    </body>
    </html>
    """

@app.route('/api/pcs', methods=['GET'])
def get_pcs():
    return jsonify(pcs_data)

@app.route('/api/pcs/refresh', methods=['POST'])
def refresh_pcs():
    try:
        for pc in pcs_data:
            if pc['status'] not in ['backup', 'inactive', 'conflict']:
                pc['cpu'] = random.randint(20, 80)
                pc['ram'] = random.randint(20, 90)
                pc['disk'] = random.randint(15, 55)
            elif pc['status'] == 'inactive':
                pc['cpu'] = 0
                pc['ram'] = 0
                pc['disk'] = 0
            pc['last_updated'] = datetime.now().strftime('%H:%M:%S')
        emit_pc_update()
        return jsonify({'success': True, 'message': 'PC data refreshed', 'pcs': pcs_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/pcs/<pc_id>/action', methods=['POST'])
def pc_action(pc_id):
    data = request.get_json()
    action = data.get('action')

    pc = next((p for p in pcs_data if p['id'] == pc_id), None)
    if not pc:
        return jsonify({'success': False, 'message': 'PC not found'}), 404

    try:
        message = ""
        if action == 'restart':
            pc.update({
                'status': 'active',
                'cpu': random.randint(10, 40),
                'ram': random.randint(20, 60),
                'disk': random.randint(10, 30)
            })
            message = f'{pc_id} restarted'
        elif action == 'shutdown':
            pc.update({
                'cpu': 0,
                'ram': 0,
                'disk': 0,
                'status': 'inactive'
            })
            message = f'{pc_id} shutdown'
        elif action == 'resolve' and pc['status'] == 'conflict':
            pc.update({
                'status': 'active',
                'cpu': random.randint(10, 40),
                'ram': random.randint(20, 60),
                'disk': random.randint(10, 30)
            })
            message = f'{pc_id} conflict resolved'
        elif action == 'assign' and pc['status'] == 'active':
            pc.update({
                'status': 'user',
                'cpu': random.randint(40, 80),
                'ram': random.randint(50, 90),
                'disk': random.randint(20, 50)
            })
            message = f'{pc_id} assigned to user'
        elif action == 'release' and pc['status'] == 'user':
            pc.update({
                'status': 'active',
                'cpu': random.randint(10, 40),
                'ram': random.randint(20, 60),
                'disk': random.randint(10, 30)
            })
            message = f'{pc_id} released'
        else:
            return jsonify({'success': False, 'message': 'Invalid action or status for this action'}), 400

        pc['last_updated'] = datetime.now().strftime('%H:%M:%S')
        emit_pc_update(pc_id)
        return jsonify({'success': True, 'message': message, 'pc': pc})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)