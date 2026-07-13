import streamlit as st
import trimesh
import numpy as np
import tempfile
import os
import plotly.graph_objects as go

st.set_page_config(page_title="焊接工装设计副驾驶", layout="wide")
st.title("🔧 焊接工装设计副驾驶 (钣金简易版)")
st.markdown("上传你的钣金 STEP 模型，获取老师傅的工装设计思路")

uploaded_file = st.file_uploader(
    "上传 3D 模型 (支持 STL / STEP 格式)", 
    type=["stl", "stp", "step"]
)

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    with st.spinner("正在加载模型，请稍候..."):
        try:
            if file_extension in ['stp', 'step']:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.stp') as tmp_input:
                    tmp_input.write(file_bytes)
                    tmp_input_path = tmp_input.name
                
                loaded = trimesh.load(tmp_input_path, file_type='stp')
                os.unlink(tmp_input_path)
                
                if isinstance(loaded, trimesh.Scene):
                    meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
                    if not meshes:
                        raise ValueError("未找到任何有效的三角网格")
                    mesh = trimesh.util.concatenate(meshes)
                else:
                    mesh = loaded
                
                if mesh.vertices.shape[0] == 0:
                    raise ValueError("网格不包含任何顶点")
                
                vertices = mesh.vertices.copy()
                max_extent = np.max(np.ptp(vertices, axis=0))
                if max_extent < 10.0:
                    st.info(f"🔍 检测到模型尺寸过小 ({max_extent:.2f} mm)，疑似单位读取错误。已自动缩放 1000 倍（将米转换为毫米）。")
                    vertices *= 1000.0
                    mesh.vertices = vertices  # 更新网格
                
                bbox = mesh.bounding_box.extents
                face_count = len(mesh.faces)
                
            else:  # STL
                mesh = trimesh.load(uploaded_file, file_type='stl')
                vertices = mesh.vertices
                bbox = mesh.bounding_box.extents
                face_count = len(mesh.faces)
                
        except Exception as e:
            st.error(f"❌ 无法加载或解析文件，错误信息：{e}")
            st.info("💡 提示：请确认上传的是有效的 STEP (.stp) 或 STL (.stl) 文件。")
            st.stop()

    # --- 将模型平移到原点，便于显示 ---
    center = np.mean(vertices, axis=0)
    vertices_centered = vertices - center
    faces = mesh.faces

    # --- 显示模型预览 ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📐 工件预览")
        
        # 计算模型大小，确定相机距离
        diag = np.linalg.norm(bbox)
        if diag < 1e-6:
            diag = 1.0
        camera_dist = diag * 2.5

        fig = go.Figure(data=[
            go.Mesh3d(
                x=vertices_centered[:,0],
                y=vertices_centered[:,1],
                z=vertices_centered[:,2],
                i=faces[:,0],
                j=faces[:,1],
                k=faces[:,2],
                color='#FF9900',
                opacity=0.85,
                flatshading=False,   # 使用平滑着色，看起来更自然
                lighting=dict(ambient=0.5, diffuse=0.8, roughness=0.5)
            )
        ])

        fig.update_layout(
            scene=dict(
                xaxis=dict(visible=False),   # 隐藏坐标轴，让视图更干净
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
                aspectmode='data',           # 自动等比例，根据数据范围调整
                camera=dict(
                    eye=dict(x=camera_dist, y=camera_dist, z=camera_dist),
                    center=dict(x=0, y=0, z=0)
                ),
                # 使用正交投影避免透视变形
                camera=dict(
                    eye=dict(x=camera_dist, y=camera_dist, z=camera_dist),
                    center=dict(x=0, y=0, z=0),
                    projection=dict(type='orthographic')
                )
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=550,
            # 强制使用场景设置
            autosize=True
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 模型信息")
        st.write(f"**尺寸 (长×宽×高)**: {bbox[0]:.1f} × {bbox[1]:.1f} × {bbox[2]:.1f} mm")
        st.write(f"**三角面片数**: {face_count:,}")
        st.write(f"**文件格式**: {file_extension.upper()}")
        st.write(f"**顶点范围 (X)**: [{vertices[:,0].min():.1f}, {vertices[:,0].max():.1f}]")
        st.write(f"**顶点范围 (Y)**: [{vertices[:,1].min():.1f}, {vertices[:,1].max():.1f}]")
        st.write(f"**顶点范围 (Z)**: [{vertices[:,2].min():.1f}, {vertices[:,2].max():.1f}]")

    # --- 以下产品类型和分析逻辑保持不变（省略，与之前一致）---
    # ...（建议保留之前完整的建议生成代码，这里不再重复）...
