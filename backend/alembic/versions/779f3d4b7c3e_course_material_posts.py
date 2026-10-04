"""course material posts

Revision ID: 779f3d4b7c3e
Revises: c8e88b2e36b2
Create Date: 2026-10-04 15:00:43.587632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '779f3d4b7c3e'
down_revision: Union[str, Sequence[str], None] = 'c8e88b2e36b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Материал курса становится постом: название, текст и сколько угодно файлов.

    Каждый существующий материал-файл превращается в материал с этим файлом,
    название — имя файла.
    """
    op.create_table('course_material_files',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('material_id', sa.Uuid(), nullable=False),
    sa.Column('file_key', sa.String(), nullable=False),
    sa.Column('file_name', sa.String(), nullable=False),
    sa.Column('file_size', sa.BigInteger(), nullable=False),
    sa.Column('content_type', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('file_size >= 0', name=op.f('ck_course_material_files_file_size_non_negative')),
    sa.ForeignKeyConstraint(['material_id'], ['course_materials.id'], name=op.f('fk_course_material_files_material_id_course_materials'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_course_material_files')),
    sa.UniqueConstraint('file_key', name=op.f('uq_course_material_files_file_key'))
    )
    op.create_index(op.f('ix_course_material_files_material_id'), 'course_material_files', ['material_id'], unique=False)
    op.add_column('course_materials', sa.Column('title', sa.String(), nullable=True))
    op.add_column('course_materials', sa.Column('text', sa.Text(), nullable=True))
    op.add_column('course_materials', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    op.execute(
        "INSERT INTO course_material_files"
        " (id, material_id, file_key, file_name, file_size, content_type, created_at)"
        " SELECT id, id, file_key, file_name, file_size, content_type, created_at"
        " FROM course_materials"
    )
    op.execute("UPDATE course_materials SET title = file_name, updated_at = created_at")
    op.alter_column('course_materials', 'title', nullable=False)

    op.drop_constraint(op.f('uq_course_materials_file_key'), 'course_materials', type_='unique')
    op.drop_constraint(op.f('ck_course_materials_file_size_non_negative'), 'course_materials', type_='check')
    op.drop_column('course_materials', 'file_name')
    op.drop_column('course_materials', 'file_size')
    op.drop_column('course_materials', 'file_key')
    op.drop_column('course_materials', 'content_type')


def downgrade() -> None:
    """Возвращает материал-файл. Откат без потерь возможен, только если у каждого материала
    ровно один файл, нет текста и название совпадает с именем файла — иначе отказ.
    """
    lossy = op.get_bind().scalar(sa.text(
        "SELECT EXISTS ("
        " SELECT 1 FROM course_materials m"
        " LEFT JOIN course_material_files f ON f.material_id = m.id"
        " GROUP BY m.id, m.title, m.text"
        " HAVING count(f.id) <> 1 OR m.text IS NOT NULL OR m.title <> min(f.file_name)"
        ")"
    ))
    if lossy:
        raise RuntimeError(
            "Откат потеряет данные: есть материалы с текстом, без файла, с несколькими"
            " файлами или с названием не по имени файла"
        )

    op.add_column('course_materials', sa.Column('content_type', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('course_materials', sa.Column('file_key', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('course_materials', sa.Column('file_size', sa.BIGINT(), autoincrement=False, nullable=True))
    op.add_column('course_materials', sa.Column('file_name', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.execute(
        "UPDATE course_materials m SET file_key = f.file_key, file_name = f.file_name,"
        " file_size = f.file_size, content_type = f.content_type"
        " FROM course_material_files f WHERE f.material_id = m.id"
    )
    for column in ('content_type', 'file_key', 'file_size', 'file_name'):
        op.alter_column('course_materials', column, nullable=False)
    op.create_unique_constraint(op.f('uq_course_materials_file_key'), 'course_materials', ['file_key'])
    op.create_check_constraint(op.f('ck_course_materials_file_size_non_negative'), 'course_materials', 'file_size >= 0')
    op.drop_column('course_materials', 'updated_at')
    op.drop_column('course_materials', 'text')
    op.drop_column('course_materials', 'title')
    op.drop_index(op.f('ix_course_material_files_material_id'), table_name='course_material_files')
    op.drop_table('course_material_files')
