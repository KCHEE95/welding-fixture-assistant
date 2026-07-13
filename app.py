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
                
                # --- 单位修正 ---
                max_extent = np.max(np.ptp(vertices, axis=0))
                if max_extent < 10.0:
                    st.info(f"🔍 检测到模型尺寸过小 ({max_extent:.2f} mm)，已自动缩放 1000 倍。")
                    vertices *= 1000.0
                    mesh.vertices = vertices
                
                # --- 【新增】姿态矫正 ---
                # 计算包围盒尺寸
                bbox = mesh.bounding_box.extents
                # 如果 Z 方向尺寸明显小于 X 或 Y，说明模型是“躺”着的
                if bbox[2] < bbox[0] * 0.8 and bbox[2] < bbox[1] * 0.8:
                    st.info("🔄 检测到模型可能处于“躺卧”姿态，正在自动旋转使其“站立”...")
                    # 绕 X 轴旋转 -90 度，让原来的 Y 方向变成 Z 方向
                    rotation_matrix = trimesh.transformations.rotation_matrix(
                        -np.pi/2, [1, 0, 0]
                    )
                    mesh.apply_transform(rotation_matrix)
                    vertices = mesh.vertices.copy()
                    bbox = mesh.bounding_box.extents
                    st.write(f"**矫正后尺寸**: {bbox[0]:.1f} × {bbox[1]:.1f} × {bbox[2]:.1f} mm")
                
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

    # --- 平移到原点 ---
    center = np.mean(vertices, axis=0)
    vertices_centered = vertices - center
    faces = mesh.faces

    # --- 显示模型预览 ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📐 工件预览")
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
                flatshading=False,
                lighting=dict(ambient=0.5, diffuse=0.8, roughness=0.5)
            )
        ])

        fig.update_layout(
            scene=dict(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
                aspectmode='data',
                camera=dict(
                    eye=dict(x=camera_dist, y=camera_dist, z=camera_dist),
                    center=dict(x=0, y=0, z=0),
                    projection=dict(type='orthographic')
                )
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=550
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

    # --- 以下分析逻辑保持不变（省略，完整代码在下方）---
    product_type = st.selectbox(
        "请选择您要焊接的产品类型（帮助提供针对性建议）",
        ["L型角钢带三角支撑", "平板拼接", "其他 / 自定义"]
    )

    if st.button("🧠 生成工装设计思路", type="primary"):
        st.subheader("📋 老师傅的设计建议")
        st.divider()

        base_x = bbox[0] + 120
        base_y = bbox[1] + 120
        clamp_count = 3 if bbox[0] > 300 else 2

        if product_type == "L型角钢带三角支撑":
            st.markdown(f"""
            **基于您选择的“L型角钢 + 三角板满焊”结构，量身定制建议如下：**

            **1. 摆放姿态**  
            将 L 型角钢的**底面**朝下平放于工装底板上，三角板保持**垂直向上**焊接。  
            （最大平面朝下，利于稳定）

            **2. 底板尺寸**  
            建议切割一块 **{base_x:.0f} × {base_y:.0f} × 10 mm** 的钢板作为底座（比工件长宽各大 60~100 mm）。

            **3. 定位方案**  
            - 使用两块 **L 型限位块**（折弯 90°，厚度 8 mm）卡住角钢的两个外直角边，限制 X/Y 方向移动。  
            - 在角钢两端各加一块 **端面挡块**（厚度 8 mm），防止轴向窜动。

            **4. 三角板支撑**  
            在三角板正下方的底板上，焊接一个 **支撑台**（高度需匹配三角板底边位置），托住三角板，保证垂直度。

            **5. 快速夹钳布局**  
            - 在角钢平面上方布置 **{clamp_count} 个垂直式快速夹钳**（如 GH-301），均匀分布，向下压紧。  
            - 在三角板顶部侧面安装 **1 个水平式推拉夹钳**，防止焊接时向后倾倒。  
            - 在三角板正面（焊缝对面）再加 **1 个推拉夹钳**，顶紧消除间隙。

            **6. 下料清单（供 SW48 切割）**  
            - 底板 × 1 (10mm 钢板)  
            - L 型限位块 × 2 (8mm 钢板，需折弯)  
            - 端面挡块 × 2 (8mm 钢板)  
            - 三角支撑台 × 1 (10mm 钢板，高度按需)  
            - 夹钳安装座 × {clamp_count + 2} 块小钣金

            **7. 焊接特别叮嘱（非常重要）**  
            ⚠️ 满焊热量大，必须严格按顺序操作：  
            - 先点焊定位三角板，确认垂直度。  
            - 采用 **对称分段焊**：左边焊 50mm 立刻跳到右边焊 50mm，反复交替，**严禁**从一头连续焊到尾。  
            - 焊后 **保持夹紧状态自然冷却 5~10 分钟**，再松开工装，否则角钢会严重变形。
            """)

        elif product_type == "平板拼接":
            st.markdown(f"""
            **基于“平板拼接”件的工装建议：**

            - 以**最大平面**为基准，平放在底板上。  
            - 底板建议尺寸：{base_x:.0f} × {base_y:.0f} × 10 mm。  
            - 周边布置限位块，并采用 **{clamp_count} 个快速夹钳** 压紧。  
            - 注意夹钳位置要避开焊缝路径，保证焊枪操作空间。  
            - 若拼接板较薄，可增加支撑点防止下塌。
            """)

        else:
            st.markdown(f"""
            **通用工装设计原则（适用于大多数钣金焊接件）：**

            1. **定位基准**：优先选择工件上最大的平面或精度要求最高的面作为基准。  
            2. **3-2-1 定位规则**：限制 6 个自由度（3 个支撑点确定基准面，2 个点限制平移，1 个点限制旋转）。  
            3. **夹紧力**：作用点应靠近定位支撑面，且不引起工件变形。  
            4. **标准件优先**：尽量使用标准快速夹钳（如 GH 系列），降低制造成本。  
            5. **空间预留**：工装设计要便于装卸工件，且不妨碍焊枪移动。  
            6. **底板推荐尺寸**：{base_x:.0f} × {base_y:.0f} × 10 mm，根据实际工件调整。
            """)

        st.success("💡 拿到以上建议后，你可以在 SolidWorks 中快速绘制各钣金件，导出 DXF 用 SW48 切割，然后点焊组装成简易工装。")
        st.info("📌 提示：本工具为设计辅助，最终工装需结合实际工艺微调。")
