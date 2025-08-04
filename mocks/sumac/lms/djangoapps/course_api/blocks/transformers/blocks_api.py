"""
Blocks API Transformer
"""


from openedx.core.djangoapps.content.block_structure.transformer import BlockStructureTransformer



class BlocksAPITransformer(BlockStructureTransformer):
    """
    Umbrella transformer that contains all the transformers needed by the
    Course Blocks API.

    Contained Transformers (processed in this order):
        StudentViewTransformer
        BlockCountsTransformer
        BlockDepthTransformer
        BlockNavigationTransformer

    Note:
        * BlockDepthTransformer must be executed before BlockNavigationTransformer.
        * StudentViewTransformer must be executed before VideoBlockURLTransformer.
    """

    WRITE_VERSION = 1
    READ_VERSION = 1
    STUDENT_VIEW_DATA = 'student_view_data'
    STUDENT_VIEW_MULTI_DEVICE = 'student_view_multi_device'

    def __init__(self, block_types_to_count, requested_student_view_data, depth=None, nav_depth=None):
        self.block_types_to_count = block_types_to_count
        self.requested_student_view_data = requested_student_view_data
        self.depth = depth
        self.nav_depth = nav_depth

    @classmethod
    def name(cls):
        return "blocks_api"